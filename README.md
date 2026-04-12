# plugindemo-python (Port von plugin-demo-java)

Dieses Projekt ist eine Python/FastAPI-Portierung der REST-API aus `plugin-demo-java`.
Der Fokus liegt auf denselben Endpoints + dem Demo-Plugin **Uhr1**.

## Start (Docker)
```bash
docker compose up --build
```

## Wichtige Endpoints
- `GET /ping`  → `pong`
- `GET /plugindemo/open/ping` → `pong`
- `GET /info` und `GET /plugindemo/open/info` → `ServiceInfoDTO`

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

Für Proxy-Setups wird zusätzlich derselbe Satz unter `/plugindemo/open/*` angeboten.

Externe Open-API (wie Java `@RequestMapping("/plugindemo/api/open")`):
- `GET  /plugindemo/api/open/pluginlist`
- `GET  /plugindemo/api/open/generalinfolist`
- `POST /plugindemo/api/open/generalinfo`
- `POST /plugindemo/api/open/reloadplugindto`
