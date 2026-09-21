# plugin-python 



## Build des Docker-Containers (build.bat)
```bash
docker build -t klausstocker/letto-plugin-python:latest -f Dockerfile .
```

## Docker Hub images

GitHub Actions builds the plugin and Jobe images for AMD64 and ARM64 and publishes
them to Docker Hub after pushes to `main` or `master`, version tags, and manual
workflow runs:

- `klausstocker/letto-plugin-python`
- `klausstocker/letto-plugin-python-jobe`

Configure these **repository secrets** (not environment secrets) before running
the workflow:

- `DOCKERHUB_USERNAME`: Docker Hub username (`klausstocker`)
- `DOCKERHUB_TOKEN`: a Docker Hub personal access token with read/write access

In GitHub, open **Settings → Secrets and variables → Actions**, select the
**Secrets** tab, scroll down past **Environment secrets** to **Repository
secrets**, and click **New repository secret**. Create each secret separately:

1. Set the name to `DOCKERHUB_USERNAME`, set its value to `klausstocker`, and
   click **Add secret**.
2. Click **New repository secret** again, set the name to `DOCKERHUB_TOKEN`,
   paste a Docker Hub personal access token as its value, and click **Add
   secret**.

For this repository, the settings page is
<https://github.com/klausstocker/plugin-python/settings/secrets/actions>. The
workflow does not use the **Environment secrets** section shown above
**Repository secrets** on that page. Never commit or paste a Docker Hub token
into an issue, pull request, source file, or chat. Revoke and replace any token
that has been exposed.

Pull requests build both images for validation but do not log in or push them.
Therefore, a successful pull-request check does **not** mean an image was
published. Merge the pull request into `main` or `master`, or open **Actions →
Build and publish Docker images → Run workflow** to publish. A default-branch
push or a manual run publishes both `latest` and `sha-<commit>` tags. Every Git
tag that is also a valid Docker tag automatically starts the workflow and is
published unchanged for both images. For example, Git tag `v1.2.3` publishes
`klausstocker/letto-plugin-python:v1.2.3` and
`klausstocker/letto-plugin-python-jobe:v1.2.3`. The workflow run summary lists
the exact tags or explains why publishing was skipped.

Create and push a release tag with:

```bash
git switch main
git pull --ff-only
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin v1.2.3
```

Docker tags may contain only letters, digits, dots, underscores, and dashes,
must start with a letter, digit, or underscore, and may be at most 128
characters long. The workflow rejects an incompatible Git tag rather than
silently publishing it under a different name.

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
  2. Wenn Git verfügbar ist, verwendet `build.bat` `git -C "%~dp0." log -1 --format=%h`; andernfalls nutzt es `unknown`. Der Wert wird als Docker-Build-Argument `PLUGIN_BUILD_HASH` übergeben.
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
