# PythonCppPlugin

One application container registers two independent LeTTo plugin types:
`Python` and `Cpp`. Both use the same Jobe container. The Docker container and
service registration name is `PythonCppPlugin`; image repositories use lowercase
`klausstocker/python-cpp-plugin` and `klausstocker/python-cpp-plugin-jobe`.

The Python execution URLs remain under `/pluginpython`. The C/C++ plugin uses
`/plugincpp/run`, `/plugincpp/check`, `/plugincpp/scorePlugin` and
`/plugincpp/example`, with its own `CppScript.js` and `CppConfigScript.js`.
The shared `/open/pluginlist` and `/open/generalinfolist` advertise both types.
Execution endpoints use the same token authentication and uploaded-file storage.

Open `http://localhost:8209/plugincpp/dev/config` for the C/C++ development dialog.
Select C17 or C++17 for answers; teacher tests always use Catch2 and C++17.
The three C/C++ examples cover functions, stdout and file access. Their starter
code intentionally needs completing. Each Catch2 TEST_CASE contributes one
equally weighted case to the grade. Student Run Code needs a main function;
function answers evaluated through Catch2 can omit main.

Switching the answer language shows a reminder to check the template and test
forward declarations. C answers need C linkage (`extern "C"`); C++ answers use
C++ linkage. The bundled tests use `__has_include("answer.c")` to define
`ANSWER_LINKAGE` automatically, so the same tests work after switching languages.
The C/C++ help includes this pattern for custom tests. The tests themselves are
always C++, so `__cplusplus` cannot distinguish the answer language.

C/C++ overview help is in `resources/plugins/Cpp/Cpp.html`; detailed help is in
`resources/help/Cpp.html` and served at `/plugincpp/help`. Its static resources
are served at `/plugincpp/static/`. Python help remains separate.

For the first deployment after the Docker rename, stop the previous Compose
project before starting the new one, because both use ports 8209 and 4000:

On the Linux playground, run the cleanup script before installing the new files:

```bash
sudo bash migrate-old-plugin.sh --dry-run
sudo bash migrate-old-plugin.sh
```

It stops only `letto-pluginpython` and `letto-jobe`, and removes the legacy
`/opt/letto/docker/compose/letto/docker-service-pluginpython.yml` and
`/opt/letto/docker/proxy/pluginpython.conf`. Already-installed replacement files
are kept. Optional positional arguments select another Compose directory and
proxy directory. Install the new files afterwards, start the new deployment,
then validate and reload the proxy. Container data and volumes are retained.

For local Windows development, use:

```powershell
docker compose -p letto-plugin-python --env-file .env.docker-local -f yml/docker-service-pluginpythoncpp.yml down --remove-orphans
.\build.bat --no-push
.\start_development.bat
```

This stops the previous containers without deleting their persistent volumes.
Compose now uses project `python-cpp-plugin`, service `pythoncppplugin`, and
containers `PythonCppPlugin` and `PythonCppPlugin-jobe`. Jobe retains its network
alias `jobe`. Existing file-storage and log-volume paths are retained. The proxy
configuration includes both URL prefixes. Compose uses locally built `latest`
images by default; set `PLUGIN_IMAGE_TAG` to deploy another published tag.

## Standalone development dialog

On Windows, run `build.bat --no-push` to build both images locally, then
`start_development.bat` to start them with `.env.docker-local`. The start script
enables the development UI and disables Letto registration automatically,
creates `nw-letto` if needed, and uses local images without pulling.

For local GUI tests without Letto, set `PLUGIN_DEV_UI=true` and
`PLUGIN_REGISTER_ON_READY=false` in `.env.docker-local`, then recreate the
plugin container using the local Docker commands below. The image must contain
this development router; rebuild it when testing source changes.

Open `http://localhost:8209/pluginpython/dev/config`. The dialog uses the normal
plugin execution endpoints and the Jobe container. Bundled resources are served
at `/pluginpython/dev/resources/`, for example
`/pluginpython/dev/resources/plugins/Python/PythonConfigScript.js`.
jQuery and Ace currently require internet access to their CDN.

`PLUGIN_DEV_UI` defaults to `false`. Leave it unset or false in production:
the dialog and the complete development resource mount then return 404.
Changing the flag requires restarting the plugin process.

## Plugin help

`resources/plugins/Python/Python.html` contains the short overview shown by Letto.
Detailed help lives in `resources/help/Python.html`, is included in the plugin
image, and is served at `/help` (also `/pluginpython/help` through the proxy).
The configuration dialog receives this detailed help separately from the overview.
Public plugin resources are served through FastAPI StaticFiles at `/pluginpython/static/`
(also `/static/` without the proxy prefix). Examples and the helpers download use
`/pluginpython/static/examples.html` and `/pluginpython/static/helpers.py` in both
development and production. Configuration help loads logos from the same static
mount and does not require LeTTo resources. The short overview still uses
`/images/plugins/Python/` from the synchronized resources directory. The dialog
resolves these links using its `serviceBase`; no Letto `/images/` mount is required.

## Teaching examples

See [the examples guide](examples/README.md) for ten small examples, from printed
output to SQLite, with typed student templates and working reference solutions.
The Docker build generates an HTML version in the plugin resources and the help
links to it.



## Build and publish Docker images

Run `build.bat` on Windows or `bash build.sh` on Linux (Bash 4+), from any
working directory. By default, both scripts build these images for the local Docker platform:

- `klausstocker/python-cpp-plugin:latest`
- `klausstocker/python-cpp-plugin-jobe:latest`

Pass `plugin` or `jobe` to build and push only that image, for example
`build.bat plugin` or `bash build.sh jobe`. The optional `--no-push` flag can
appear before or after the image argument, for example `bash build.sh jobe --no-push`.
Omit the image argument to build both images.

Docker must be running with Linux container support. Git supplies the plugin's
build hash. A source archive without `.git` uses `unknown` as the build hash.
The scripts only build and publish; use the installation instructions below to
deploy containers. GitHub Actions only validates builds on pull requests or
manual runs; it no longer logs in or uploads images.

Without a Git tag directly on `HEAD`, selected images are uploaded as `latest`. With one or more
lightweight or annotated tags on `HEAD`, selected images receive every exact Git
tag and are uploaded to Docker Hub, together with `latest`, after all selected builds
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

Install `yml/docker-service-pluginpythoncpp.yml` in
`/opt/letto/docker/compose/letto/` and configure the server's `.env` there
as described in the installation section below. Set the desired image tags
directly in the Compose file. Run the startup script from the repository,
or copy it to the server and run it from any directory:

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
run `docker login` as that account.

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

docker pull klausstocker/python-cpp-plugin:latest
docker pull klausstocker/python-cpp-plugin-jobe:latest

New-Item -ItemType Directory -Force .docker-test\log | Out-Null
New-Item -ItemType Directory -Force .docker-test\images | Out-Null
New-Item -ItemType Directory -Force .docker-test\plugins | Out-Null

@"
SERVER_NAME=localhost
SERVICE_USER_PASSWORD=test-user-password
LETTO_SETUP_URI=http://localhost:8096
LETTO_PLUGIN_URI_EXTERN=http://localhost:8209/pluginpython
VOLUME_LOG=./.docker-test/log
VOLUME_IMAGES=./.docker-test/images
VOLUME_PLUGINS=./.docker-test/plugins
"@ | Set-Content -Encoding ascii .env.docker-local

docker network inspect nw-letto *> $null
if ($LASTEXITCODE -ne 0) { docker network create nw-letto }

docker compose --env-file .env.docker-local -f yml/docker-service-pluginpythoncpp.yml config
docker compose --env-file .env.docker-local -f yml/docker-service-pluginpythoncpp.yml pull
docker compose --env-file .env.docker-local -f yml/docker-service-pluginpythoncpp.yml up -d --no-build
docker compose --env-file .env.docker-local -f yml/docker-service-pluginpythoncpp.yml ps
docker compose --env-file .env.docker-local -f yml/docker-service-pluginpythoncpp.yml logs --tail 100

curl.exe http://localhost:8209/ping
curl.exe http://localhost:4000/

docker inspect PythonCppPlugin --format '{{.Config.Image}}'
docker inspect PythonCppPlugin-jobe --format '{{.Config.Image}}'
```

Der erste Aufruf sollte `pong` liefern. Die beiden `docker inspect`-Befehle
sollten `klausstocker/python-cpp-plugin:latest` beziehungsweise
`klausstocker/python-cpp-plugin-jobe:latest` ausgeben. Der Plugin-Healthcheck
hat eine Startphase von 90 Sekunden; direkt nach dem Start kann der Status daher
zunächst `starting` sein.

Status und Logs können später erneut geprüft werden:

```powershell
docker compose --env-file .env.docker-local -f yml/docker-service-pluginpythoncpp.yml ps
docker compose --env-file .env.docker-local -f yml/docker-service-pluginpythoncpp.yml logs --follow
```

Aufräumen nach dem Test:

```powershell
docker compose --env-file .env.docker-local -f yml/docker-service-pluginpythoncpp.yml down
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
cp yml/docker-service-pluginpythoncpp.yml /opt/letto/docker/compose/letto/
cd /opt/letto/docker/compose/letto
```

Falls die Variablen nicht bereits zentral gesetzt werden, eine `.env`-Datei
neben der Compose-Datei erstellen und die Beispielwerte anpassen:

```bash
cat > .env <<'EOF'
SERVER_NAME=letto.example.org
SERVICE_USER_PASSWORD=BITTE_AENDERN
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

docker compose --env-file .env -f docker-service-pluginpythoncpp.yml config
docker compose --env-file .env -f docker-service-pluginpythoncpp.yml config --images
docker compose --env-file .env -f docker-service-pluginpythoncpp.yml pull
docker compose --env-file .env -f docker-service-pluginpythoncpp.yml up -d --no-build
```

Status, verwendete Images und Logs prüfen:

```bash
docker compose --env-file .env -f docker-service-pluginpythoncpp.yml ps
docker inspect PythonCppPlugin --format '{{.Config.Image}}'
docker inspect PythonCppPlugin-jobe --format '{{.Config.Image}}'
docker compose --env-file .env -f docker-service-pluginpythoncpp.yml logs --tail=100
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
docker compose --env-file .env -f docker-service-pluginpythoncpp.yml pull
docker compose --env-file .env -f docker-service-pluginpythoncpp.yml up -d --no-build
docker image prune -f
```

### Sauberer Neu-Download auf dem Produktionsserver

Wenn die beiden Container zuerst gestoppt und **alle lokal vorhandenen Images
dieser beiden Repositories** entfernt werden sollen, die folgenden Befehle
verwenden. Die Befehle löschen keine Volumes und keine Daten unter
`/opt/letto/docker/storage`:

```bash
cd /opt/letto/docker/compose/letto

docker compose --env-file .env -f docker-service-pluginpythoncpp.yml down --remove-orphans

for image_id in $(docker image ls \
  --filter 'reference=klausstocker/python-cpp-plugin*' \
  --quiet | sort -u); do
  docker image rm "$image_id"
done

docker image prune -f

docker compose --env-file .env -f docker-service-pluginpythoncpp.yml pull
docker compose --env-file .env -f docker-service-pluginpythoncpp.yml up -d --no-build --force-recreate
```

Danach prüfen, ob beide Container die neu heruntergeladenen Images verwenden
und erfolgreich antworten:

```bash
docker compose --env-file .env -f docker-service-pluginpythoncpp.yml ps
docker inspect PythonCppPlugin --format '{{.Config.Image}} {{.Image}}'
docker inspect PythonCppPlugin-jobe --format '{{.Config.Image}} {{.Image}}'
docker compose --env-file .env -f docker-service-pluginpythoncpp.yml logs --tail=100
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
docker compose --env-file .env -f docker-service-pluginpythoncpp.yml down
```

Sind die Docker-Hub-Repositories nicht öffentlich, muss vor `pull` einmal
`docker login` ausgeführt werden.

* Proxy Konfiguration:
  * kopiere proxy/pluginpythoncpp.conf in /opt/letto/docker/proxy/ am LeTTo-Server
  * entferne die alte pluginpython.conf, damit die location-Blöcke nicht doppelt geladen werden
  * falls nginx die Datei ausdrücklich per include lädt, ändere den Dateinamen dort ebenfalls; bei einem *.conf-Include ist keine Änderung nötig
  * prüfe vor dem Reload: docker exec letto-proxy nginx -t
  * restarte den Proxy (docker restart letto-proxy)
* Ressourcen-Synchronisierung:
  * Beim Start kopiert der Service automatisch `RESOURCE_DIR/plugins` in die gesetzten Zielpfade:
    * `${letto_pathPlugins}` (z. B. `/opt/letto/plugins`)
    * `${letto_pathImages}/plugins` (z. B. `/opt/letto/images/plugins`)

## Jobe-Integrationstests fuer C und C++

Voraussetzung ist ein laufender Jobe-Container auf `localhost:4000`.

```powershell
py -m unittest tests.test_jobe tests.test_jobe_compiled -v
```

Die C/C++-Tests pruefen Sprach-IDs und Compiler-Versionen, stdout,
Compilerfehler, Laufzeitabbruch, CPU-Zeitlimits, das Lesen und Schreiben von
Dateien sowie hochgeladene Header und zusaetzliche Quelldateien. Die
Sprachunterstuetzung wird vorausgesetzt; fehlende Sprachen lassen die Tests
fehlschlagen.

Im geprueften Entwicklungscontainer sind `c` und `cpp` mit GCC/G++ 13.3.0
verfuegbar. Jobe verwendet fuer C standardmaessig C99; explizite C17- und
C++17-Optionen funktionieren ueber `parameters.compileargs`. Eine weitere
Quelldatei kann ueber `parameters.linkargs` mitkompiliert werden. Der Python-
Wrapper bietet diese Compiler-/Linkeroptionen derzeit noch nicht an.
Die getrennte C-Kompilierung mit anschliessendem Linken gegen einen C++-
Catch2-Runner wird durch die unten beschriebenen Catch2-Tasks umgesetzt.

Ein Programm mit Exitcode 1 wird von diesem Jobe als erfolgreich ausgefuehrt
gemeldet; ein Abbruch mit `abort()` liefert dagegen Outcome 12. Catch2-
Testergebnisse muessen deshalb spaeter anhand des Testreports bewertet werden.

## Catch2 fuer C- und C++-Funktionstests

Das Jobe-Dockerfile installiert die feste stabile Version
[Catch2 3.16.0](https://github.com/catchorg/Catch2/releases/tag/v3.16.0).
Catch2 und der Test-Runner werden beim Image-Build vorkompiliert; Compiler und
CMake fuer den Catch2-Build bleiben im separaten Build-Stage.

```powershell
docker build -f jobe/Dockerfile -t klausstocker/python-cpp-plugin-jobe:1.0.0 .
```

Nach dem Neuaufsetzen des Jobe-Containers mit diesem Image bietet Jobe
zusaetzlich die internen Sprach-IDs `catch2c` und `catch2cpp` an.
`shared.check_catch2.check_catch2` akzeptiert als Abgabesprache `c` oder `cpp`:

```python
from shared.check_catch2 import check_catch2

result = check_catch2(
    "localhost:4000",
    "int calculate_sum(int a, int b) { return a + b; }",
    '''#include <catch2/catch_test_macros.hpp>
extern "C" { int calculate_sum(int, int); }
TEST_CASE("sum") { REQUIRE(calculate_sum(2, 3) == 5); }
''',
    language="c",
)
assert result.wasSuccessful()
```

C-Abgaben werden separat mit GCC als C17 kompiliert; Testcode ist C++17 und
deklariert C-Funktionen mit `extern "C"`. Bei C++-Abgaben entfaellt `extern "C"`.
Abgaben und Testcode definieren kein eigenes `main`; dieses liefert der
vorkompilierte Runner. Hochgeladene Header und Datendateien sind ueber `files`
verfuegbar. Kompilierung, Linken und Ausfuehrung erfolgen in Jobe-Sandboxes.

Der XML-Report wird getrennt von studentischem stdout erzeugt und in ein
`CheckResult` umgewandelt. Bewertet werden Testfaelle (`TEST_CASE`), keine
einzelnen Assertions. Compiler-/Linkerfehler, Laufzeitabbruch, Zeitlimit und
fehlende oder leere Reports liefern Fehler statt einer erfolgreichen Bewertung.
Die Sprachauswahl in den Plugin-Endpunkten und im Dialog folgt separat.

```powershell
py -m unittest tests.test_check_catch2 -v
```

Zum Testen eines separaten Containers kann `JOBE_TEST_SERVER` gesetzt werden,
zum Beispiel auf `localhost:4001`.

### Laufzeiten messen

Catch2 ist in jedem Build des Jobe-Dockerfiles enthalten. Der Build prueft
Bibliothek, Header, Runner und Jobe-Tasks; es ist keine Installation nach dem
Containerstart erforderlich. Aenderungen am laufenden Container allein gehen
bei dessen Neuerstellung verloren, daher fuer dauerhafte Updates das Image
mit `build.bat jobe --no-push` bauen und den Jobe-Container neu erstellen.

```powershell
py scripts/benchmark_jobe_cpp.py --runs 5
```

Der Benchmark speichert Einzelmessungen und die zurueckgegebenen XML-Reports
in `artifacts/jobe_cpp_timings.json`. `--server localhost:4001` und
`--output anderer-pfad.json` passen Server und Ausgabedatei an.
Alle Zeitangaben in der JSON-Datei sind Sekunden; die Konsolentabelle zeigt
Millisekunden. Es gibt keinen zusaetzlichen Download beliebiger Ergebnisdateien:
Der Catch2-XML-Report wird als Teil von Jobe-stdout zurueckgegeben und lokal gespeichert.

| Messung | Umfang |
| --- | --- |
| `total_client_seconds` | Von `run_test` inklusive Datei-Uploads bis zur empfangenen und dekodierten Antwort |
| `upload_and_verify_seconds` | Datei-Uploads und deren HEAD-Pruefungen inklusive kleiner Vorbereitungsarbeit |
| `run_request_seconds` | POST `/runs` bis zur empfangenen und dekodierten Antwort |
| `answer_compile_wall_seconds` | GCC/G++-Aufruf zum Kompilieren der Abgabe in eine Objektdatei |
| `test_compile_wall_seconds` | G++-Aufruf zum Kompilieren der Catch2-Testdatei |
| `link_wall_seconds` | Separater G++-Linkeraufruf mit vorkompiliertem Runner und Catch2 |
| `compile_sandbox_wall_seconds` | Alle drei Compiler-/Linkerphasen samt Python-Treiber und Sandbox-Verwaltung |
| `test_run_wall_seconds` | Catch2 `Session::run`, inklusive Framework und XML-Reporter, ohne Prozessstart |
| `execute_sandbox_wall_seconds` | Gesamte Ausfuehrungsphase inklusive Sandbox, Prozessstart und Reportausgabe |

Die drei Compiler-/Linkerphasen liefern zusaetzlich `*_cpu_seconds`, gemessen
ueber die vom Betriebssystem erfasste Benutzer- und System-CPU-Zeit ihrer
Kindprozesse. Die anderen Angaben sind monotone Wall-Clock-Zeiten. Die
Messbereiche ueberlappen; sie duerfen nicht alle addiert werden. Die Differenz
zwischen POST-Zeit und beiden Sandbox-Zeiten enthaelt unter anderem
HTTP-Verarbeitung, Arbeitsplatzvorbereitung und Aufraeumen, keine isolierte
Netzwerkzeit. Fehlgeschlagene Phasen liefern nur die bis dahin vorhandenen
Messungen; bei hartem Sandbox-Abbruch koennen innere Messungen fehlen.

Eine erste lokale Messung mit zwei sehr kleinen C++-Testfaellen ergab nach
dem ersten Lauf etwa 0,65 bis 0,68 Sekunden insgesamt. Der Median von drei
Laeufen lag bei etwa 17 ms fuer Abgabekompilierung, 360 ms fuer Testkompilierung,
117 ms fuer Linken und 0,44 ms fuer Catch2 selbst. Der erste Lauf dauerte
1,72 Sekunden; diese Werte sind eine lokale Baseline, kein Geschwindigkeitsversprechen.

### Cache fuer Catch2-Testobjekte

Jobe speichert erfolgreich kompilierte Testobjekte in `/var/cache/jobe/catch2`.
Der Docker-Entrypoint leert dieses Verzeichnis bei jedem Containerstart,
auch bei `docker restart`. Es wird kein Volume benoetigt und kein Versionsschluessel
verwendet. Fuer einen neuen Compiler oder eine neue Catch2-Version muss der
Container mit dem entsprechenden Image neu erstellt werden.

Jede Abgabe kann einen Cache-Miss fuellen; ein vorheriger Aufruf im Lehrer-Dialog
ist nicht erforderlich. Der SHA-256-Schluessel umfasst Testquelle und Dateinamen,
Test-Compilerflags, die vom Praeprozessor gefundenen lokalen Includes und alle
weiteren hochgeladenen Hilfsdateien. Aenderungen an Hilfsdateien duerfen deshalb
auch dann eine Neukompilierung ausloesen, wenn die Datei nicht verwendet wird.
Abgabeinhalte werden nur dann mitgehasht, wenn die Tests die Abgabedatei selbst
inkludieren. Andernfalls koennen verschiedene Abgaben dasselbe Testobjekt nutzen.

Abgabeobjekt und ausfuehrbares Programm werden immer neu erstellt. Bei unbekannten
externen Includes, zeitabhaengigen Makros oder nicht verfuegbarem Cache wird
konservativ neu kompiliert. Fehlerhaftes Linken mit einem gecachten Objekt wird
einmal mit frisch kompiliertem Testobjekt wiederholt. Eine fehlerhafte Kompilierung bzw. ein fehlerhaftes
Linken fuellt den Cache nicht. Assertion-Fehler im anschliessenden Testlauf
verhindern dagegen nicht die Wiederverwendung des korrekt gebauten Testobjekts.

Jobe verwaltet Cache-Locks und publiziert Objekte atomar vor der Ausfuehrung
studentischen Codes. Die Sandbox hat nur Lesezugriff auf den gemeinsamen Cache.
Parallele Abgaben mit identischem Schluessel teilen sich die erste Kompilierung.
Die erste Version hat keine Groessenbegrenzung; der Cache wird beim Start geleert.

`RunResult.timings` enthaelt `test_cache_hit` und die Zeit fuer die
Abhaengigkeitsanalyse (`test_cache_key_wall_seconds`). Bei einem Treffer sind
Testkompilierungszeiten null; Cache-Pruefung, Kopieren, Abgabekompilierung und
Linken kosten weiterhin Zeit. Der Benchmark speichert den Trefferstatus pro Lauf.

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
  - Das aktuelle Token wird in die Plugin-Daten (`params.pluginToken`) eingebettet und von den JavaScript-Clients für Requests verwendet.
- Übergabe des Tokens:
  - Bevorzugt: `Authorization: Bearer <token>`
  - Alternativ: Header `X-Plugin-Token: <token>`
  - Alternativ: Query-Parameter `?token=<token>`
- Die JavaScript-Clients (`initPluginPython`/`configPluginPython`) senden automatisch den Bearer-Token, wenn `dto.params.pluginToken` oder `dto.pluginToken` gesetzt ist.
