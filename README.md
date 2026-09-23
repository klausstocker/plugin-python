# plugin-python 



## Build and publish Docker images

Run `build.bat` on Windows or `bash build.sh` on Linux (Bash 4+), from any
working directory. Both scripts build these images for the local Docker platform:

- `klausstocker/letto-plugin-python:latest`
- `klausstocker/letto-plugin-python-jobe:latest`

Docker must be running with Linux container support. Git supplies the plugin's
build hash. A source archive without `.git` uses `unknown` as the build hash.
The scripts only build and publish; use the installation instructions below to
deploy containers. GitHub Actions only validates builds on pull requests or
manual runs; it no longer logs in or uploads images.

Without a Git tag directly on `HEAD`, both images are uploaded as `latest`. With one or more
lightweight or annotated tags on `HEAD`, both images receive every exact Git
tag and are uploaded to Docker Hub, together with `latest`, after both builds
succeed. Older tags on ancestor commits are ignored. Publishing requires a prior
`docker login`. Publishing a tagged release also requires a clean checkout
(including untracked files). Use `--no-push` to build without uploading.
Tags must match `[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}`; incompatible tags fail
before building. Any build, tagging, or upload failure stops the script with a
nonzero exit code. Docker Hub uploads are not atomic across images/tags; after
an interrupted release, rerun from the same checkout.

Build/test without uploading, even on a tagged commit:

```powershell
.\build.bat --no-push
```

```bash
bash build.sh --no-push
```

Publish a release after committing the changes:

```bash
docker login
git tag -a v1.2.3 -m "Release v1.2.3"
bash build.sh                  # Windows: .\build.bat
git push origin v1.2.3         # Records the release tag on GitHub
```

This publishes `:v1.2.3` and `:latest` for both repositories. Local scripts build
only the Docker engine's platform; the validation workflow checks AMD64 and
ARM64 but does not publish multi-platform manifests.

## Start or update production services (Linux)

Install `yml/docker-service-pluginpython.yml` in
`/opt/letto/docker/compose/letto/` and configure the server's `.env` there
as described in the installation section below. Include the image tag:

```dotenv
PLUGIN_PYTHON_TAG=v1.2.3
```

Use your published release tag or `latest`. Run the startup script from the
repository, or copy it to the server and run it from any directory:

```bash
bash start.sh
# Optional alternative deployment directory:
bash start.sh /path/to/compose-directory
```

The script validates configuration, pulls both images, ensures `nw-letto`
exists, stops the previous plugin and Jobe containers, and recreates them.
It waits up to 180 seconds for healthy containers. A failed pull leaves the
running services untouched; startup failures return a nonzero exit code without
automatic rollback. Persistent volumes and bind mounts are retained. Other
services are not stopped. Docker Compose with `--wait` support is required.
Run with an account that can access Docker; for private repositories, first
run `docker login` as that account. An exported `PLUGIN_PYTHON_TAG` overrides
the value in `.env`.

## Free Docker disk space

Run `docker-cleanup.bat` on Windows or `bash docker-cleanup.sh` on Linux.
Type `DELETE` at the prompt, or pass `--yes` for unattended execution.

These scripts affect **all projects on the Docker engine targeted by your Docker
settings**: they stop and remove all containers, prune all unused images, and
clear the selected builder's cache. Removing containers is necessary to free
their images and also deletes container logs and writable container data.
Volumes and bind-mounted files are preserved. Other Buildx builders may retain
their own caches. Avoid concurrent builds or container creation during cleanup.

The scripts stop on errors and print `docker system df` after completion.
Recreate services using Compose afterwards. On Docker Desktop, freed space
inside its virtual disk may not immediately reduce the disk file's host size.

### Lokaler Test unter Windows (PowerShell)

Die folgenden Befehle sind für **PowerShell** und setzen Docker Desktop im
Linux-Container-Modus voraus. Sie laden die veröffentlichten Images herunter,
erstellen die für Compose benötigten lokalen Verzeichnisse und das externe
Netzwerk und starten beide Container.

```powershell
cd C:\Pfad\zu\plugin-python

docker version
docker compose version

docker pull klausstocker/letto-plugin-python:latest
docker pull klausstocker/letto-plugin-python-jobe:latest

New-Item -ItemType Directory -Force .docker-test\log | Out-Null
New-Item -ItemType Directory -Force .docker-test\images | Out-Null
New-Item -ItemType Directory -Force .docker-test\plugins | Out-Null

@"
LETTO_SCHULEN=test
PLUGIN_PYTHON_TAG=latest
SERVER_NAME=localhost
SERVICE_USER_PASSWORD=test-user-password
SERVICE_GAST_PASSWORD=test-guest-password
LETTO_SETUP_URI=http://localhost:8096
LETTO_PLUGIN_URI_EXTERN=http://localhost:8209/pluginpython
VOLUME_LOG=./.docker-test/log
VOLUME_IMAGES=./.docker-test/images
VOLUME_PLUGINS=./.docker-test/plugins
"@ | Set-Content -Encoding ascii .env.docker-local

docker network inspect nw-letto *> $null
if ($LASTEXITCODE -ne 0) { docker network create nw-letto }

docker compose --env-file .env.docker-local -f yml/docker-service-pluginpython.yml config
docker compose --env-file .env.docker-local -f yml/docker-service-pluginpython.yml pull
docker compose --env-file .env.docker-local -f yml/docker-service-pluginpython.yml up -d --no-build
docker compose --env-file .env.docker-local -f yml/docker-service-pluginpython.yml ps
docker compose --env-file .env.docker-local -f yml/docker-service-pluginpython.yml logs --tail 100

curl.exe http://localhost:8209/ping
curl.exe http://localhost:4000/

docker inspect letto-pluginpython --format '{{.Config.Image}}'
docker inspect letto-jobe --format '{{.Config.Image}}'
```

Der erste Aufruf sollte `pong` liefern. Die beiden `docker inspect`-Befehle
sollten `klausstocker/letto-plugin-python:latest` beziehungsweise
`klausstocker/letto-plugin-python-jobe:latest` ausgeben. Der Plugin-Healthcheck
hat eine Startphase von 90 Sekunden; direkt nach dem Start kann der Status daher
zunächst `starting` sein.

Status und Logs können später erneut geprüft werden:

```powershell
docker compose --env-file .env.docker-local -f yml/docker-service-pluginpython.yml ps
docker compose --env-file .env.docker-local -f yml/docker-service-pluginpython.yml logs --follow
```

Aufräumen nach dem Test:

```powershell
docker compose --env-file .env.docker-local -f yml/docker-service-pluginpython.yml down
docker network rm nw-letto
Remove-Item .env.docker-local -ErrorAction SilentlyContinue
Remove-Item .docker-test -Recurse -Force -ErrorAction SilentlyContinue
```

`docker network rm nw-letto` darf ausgelassen werden, wenn andere lokale
LeTTo-Container dieses Netzwerk verwenden. Die Datei `.env.docker-local`
enthält nur Testwerte; echte Passwörter dürfen nicht eingecheckt werden.

## Installation am LeTTo-Server

Die folgenden Befehle werden auf dem Linux-Server ausgeführt. Bei Ausführung
ohne `root` muss je nach Installation `sudo` vor die Docker- und
Dateisystembefehle gesetzt werden.

Zuerst die Compose-Datei aus dem ausgecheckten Repository installieren und die
benötigten Verzeichnisse anlegen:

```bash
install -d /opt/letto/docker/compose/letto
install -d /opt/letto/docker/storage/log/pluginpython
install -d /opt/letto/docker/storage/images
install -d /opt/letto/docker/storage/plugins
cp yml/docker-service-pluginpython.yml /opt/letto/docker/compose/letto/
cd /opt/letto/docker/compose/letto
```

Falls die Variablen nicht bereits zentral gesetzt werden, eine `.env`-Datei
neben der Compose-Datei erstellen und die Beispielwerte anpassen:

```bash
cat > .env <<'EOF'
LETTO_SCHULEN=meine-schule
PLUGIN_PYTHON_TAG=latest
SERVER_NAME=letto.example.org
SERVICE_USER_PASSWORD=BITTE_AENDERN
SERVICE_GAST_PASSWORD=BITTE_AENDERN
TIMEZONE=Europe/Berlin
LOCALE=de_DE.UTF-8
EOF
chmod 600 .env
```

Das in der Compose-Datei als extern deklarierte Netzwerk muss bereits
existieren. Anschließend die Konfiguration prüfen, beide Images herunterladen
und beide Container starten:

```bash
docker network inspect nw-letto >/dev/null 2>&1 || docker network create nw-letto

docker compose --env-file .env -f docker-service-pluginpython.yml config
docker compose --env-file .env -f docker-service-pluginpython.yml config --images
docker compose --env-file .env -f docker-service-pluginpython.yml pull
docker compose --env-file .env -f docker-service-pluginpython.yml up -d --no-build
```

Status, verwendete Images und Logs prüfen:

```bash
docker compose --env-file .env -f docker-service-pluginpython.yml ps
docker inspect letto-pluginpython --format '{{.Config.Image}}'
docker inspect letto-jobe --format '{{.Config.Image}}'
docker compose --env-file .env -f docker-service-pluginpython.yml logs --tail=100
```

Die lokalen Endpunkte testen:

```bash
curl --fail http://localhost:8209/ping
curl --fail http://localhost:4000/
```

Der erste Befehl muss `pong` liefern. Beim Aktualisieren auf neu veröffentlichte
Images genügen folgende Befehle:

```bash
cd /opt/letto/docker/compose/letto
docker compose --env-file .env -f docker-service-pluginpython.yml pull
docker compose --env-file .env -f docker-service-pluginpython.yml up -d --no-build
docker image prune -f
```

### Sauberer Neu-Download auf dem Produktionsserver

Wenn die beiden Container zuerst gestoppt und **alle lokal vorhandenen Images
dieser beiden Repositories** entfernt werden sollen, die folgenden Befehle
verwenden. Die Befehle löschen keine Volumes und keine Daten unter
`/opt/letto/docker/storage`:

```bash
cd /opt/letto/docker/compose/letto

docker compose --env-file .env -f docker-service-pluginpython.yml down --remove-orphans

for image_id in $(docker image ls \
  --filter 'reference=klausstocker/letto-plugin-python*' \
  --quiet | sort -u); do
  docker image rm "$image_id"
done

docker image prune -f

docker compose --env-file .env -f docker-service-pluginpython.yml pull
docker compose --env-file .env -f docker-service-pluginpython.yml up -d --no-build --force-recreate
```

Danach prüfen, ob beide Container die neu heruntergeladenen Images verwenden
und erfolgreich antworten:

```bash
docker compose --env-file .env -f docker-service-pluginpython.yml ps
docker inspect letto-pluginpython --format '{{.Config.Image}} {{.Image}}'
docker inspect letto-jobe --format '{{.Config.Image}} {{.Image}}'
docker compose --env-file .env -f docker-service-pluginpython.yml logs --tail=100
curl --fail http://localhost:8209/ping
curl --fail http://localhost:4000/
```

Auf einem Server mit weiteren Docker-Anwendungen nicht `docker system prune -a`
oder `docker volume prune` verwenden: Diese Befehle können Images,
Build-Caches oder Daten anderer Anwendungen löschen. Der oben verwendete
Repository-Filter begrenzt das Löschen auf die beiden Plugin-Python-Images.

Zum Stoppen und Entfernen der beiden Container, ohne die persistenten Daten zu
löschen:

```bash
cd /opt/letto/docker/compose/letto
docker compose --env-file .env -f docker-service-pluginpython.yml down
```

Sind die Docker-Hub-Repositories nicht öffentlich, muss vor `pull` einmal
`docker login` ausgeführt werden.

* Proxy Konfiguration:
  * kopiere proxy/pluginpython.conf in /opt/letto/docker/proxy/ am LeTTo-Server 
  * restarte den Proxy (docker restart letto-proxy)
* Ressourcen-Synchronisierung:
  * Beim Start kopiert der Service automatisch `RESOURCE_DIR/plugins` in die gesetzten Zielpfade:
    * `${letto_pathPlugins}` (z. B. `/opt/letto/plugins`)
    * `${letto_pathImages}/plugins` (z. B. `/opt/letto/images/plugins`)

## Wichtige Endpoints
- `GET /ping`  → `pong`
- `GET /pluginpython/open/ping` → `pong`
- `GET /info` und `GET /pluginpython/open/info` → `ServiceInfoDTO`

Interne Plugin-API (wie Java `@RequestMapping("/open")`):
- `GET  /open/pluginlist`
- `GET  /open/generalinfolist`
- `POST /open/generalinfo` (Body ist **String** wie in Java)
- `POST /open/gethtml`
- `POST /open/angabe`
- `POST /open/image`
- `POST /open/loadplugindto`
- `POST /open/score`
- ...

Für Proxy-Setups wird zusätzlich derselbe Satz unter `/pluginpython/open/*` angeboten.

Externe Open-API (wie Java `@RequestMapping("/pluginpython/api/open")`):
- `GET  /pluginpython/api/open/pluginlist`
- `GET  /pluginpython/api/open/generalinfolist`
- `POST /pluginpython/api/open/generalinfo`
- `POST /pluginpython/api/open/reloadplugindto`


## Build-/Commit-Anzeige im Konfigurationsdialog
- Der Konfigurationsdialog zeigt den direkt im JavaScript eingebetteten Build-Hash und den vom Backend-Endpunkt `GET /pluginpython/buildhash` gemeldeten Hash im Tab `Configuration` an. Wenn beide Werte abweichen, werden beide rot markiert.
- Der JavaScript-Wert steht als String direkt in `resources/plugins/Python/PythonConfigScript.js` (`PYTHON_CONFIG_SCRIPT_COMMIT_HASH`) und wird nicht vom Python-Backend in die JavaScript-Parameter injiziert; der Backend-Endpunkt liest denselben Build-Wert aus `PLUGIN_BUILD_HASH`.
- Automatische Aktualisierung:
  1. `build.bat` läuft relativ zu seinem eigenen Verzeichnis (`%~dp0`) und fragt Git nur ab, wenn dort `.git` existiert. Dadurch wird `fatal: Needed a single revision` vermieden, wenn das Skript außerhalb eines Git-Checkouts liegt.
  2. Wenn Git verfügbar ist, verwendet `build.bat` `git -C "%~dp0." rev-parse --short HEAD`; ohne `.git` nutzt es `unknown`. Der Wert wird als Docker-Build-Argument `PLUGIN_BUILD_HASH` übergeben.
  3. Das Dockerfile ersetzt beim Image-Build den String in der kopierten `PythonConfigScript.js`, sodass die ausgelieferte JavaScript-Datei den Build-Commit direkt enthält.
- Für CI/CD sollte entsprechend `docker build --build-arg PLUGIN_BUILD_HASH=$(git log -1 --format=%h 2>/dev/null || echo unknown) ...` verwendet werden.

## Absicherung der Code-Execution-Endpunkte
- Betroffene Endpunkte: `POST /pluginpython/run`, `POST /pluginpython/lint`, `POST /pluginpython/check`, `POST /pluginpython/example`.
- Optional aktivierbar über Umgebungsvariablen:
  - `PLUGIN_EXEC_REQUIRE_TOKEN` ist standardmäßig `true` (Prüfung ist damit standardmäßig aktiv).
- Token-Quelle:
  - Das Service erzeugt beim Start automatisch ein neues `EXEC_TOKEN` (zufällig, pro Prozessstart neu).
  - `PLUGIN_EXEC_TOKEN` aus der Umgebung wird **nicht** verwendet.
  - Das aktuelle Token wird in die Plugin-Daten (`params.pluginToken`) eingebettet und von den JavaScript-Clients für Requests verwendet.
- Übergabe des Tokens:
  - Bevorzugt: `Authorization: Bearer <token>`
  - Alternativ: Header `X-Plugin-Token: <token>`
  - Alternativ: Query-Parameter `?token=<token>`
- Die JavaScript-Clients (`initPluginPython`/`configPluginPython`) senden automatisch den Bearer-Token, wenn `dto.params.pluginToken` oder `dto.pluginToken` gesetzt ist.
