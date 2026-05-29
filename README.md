# plugin-python 



## Build des Docker-Containers (build.bat)
```bash
docker build -t letto-plugin-python:latest -f Dockerfile .
```

## Installation am LeTTo-Server
* Installation des Docker-Containers:
  * kopiere yml/docker-service-pluginpython.yml in /opt/letto/docker/compose/letto/ am LeTTo-Server 
  * starte den Container (docker compose -f /opt/letto/docker/compose/letto/ docker-service-pluginpython.yml up -d)
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
- Der Konfigurationsdialog zeigt `Plugin build: <hash>` im Tab `Configuration` an.
- Der Wert kommt aus `params.buildHash`, das vom Backend in die Plugin-Daten geschrieben wird.
- Automatische Aktualisierung:
  1. `build.bat` ermittelt vor `docker build` automatisch `git rev-parse --short=12 HEAD`.
  2. Der Wert wird als Docker-Build-Argument `PLUGIN_BUILD_HASH` übergeben.
  3. Das Dockerfile übernimmt ihn als Image-Label `org.opencontainers.image.revision` und als Environment-Variable `PLUGIN_BUILD_HASH`.
  4. Zur Laufzeit verwendet das Backend `PLUGIN_BUILD_HASH`; in lokalen Entwicklerversionen fällt es auf `git rev-parse --short=12 HEAD` und danach auf `revision.txt` zurück.
- Für CI/CD sollte entsprechend `docker build --build-arg PLUGIN_BUILD_HASH=$(git rev-parse --short=12 HEAD) ...` verwendet werden.

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
