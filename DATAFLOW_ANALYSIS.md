# Plugin Python Dataflow (LeTTo setup -> browser -> plugin service)

## 1) Service startup and setup registration
- On app startup (`lifespan`), the plugin first synchronizes web resources and then starts async registration against LeTTo setup.
- Registration payload declares the plugin service metadata and key internal/external URIs.

## 2) How LeTTo discovers and loads the JS
- The setup/host calls `/open/generalinfo` (or list variant).
- `plugin_general_info()` returns `initPluginJS = initPluginPython` and embeds local JavaScript library contents from:
  - `plugins/Python/PythonScript.js`
  - `plugins/Python/PythonConfigScript.js`

## 3) Runtime question rendering dataflow
- LeTTo requests `/open/loadplugindto` (or `/open/reloadplugindto`).
- Service returns `PluginDto` with `tagName`, dimensions, and image data URL (`imageUrl`), optionally params/config.
- In browser, LeTTo executes `initPluginPython(dtoString, active)` from `PythonScript.js`.
- JS builds editor UI, binds hidden answer input (`.<tag>_inp`), and initializes code content from answer field or `dto.jsonData.indication`.

## 4) Browser -> plugin execution feedback loop
- Clicking **Run Code** / **Lint Code** triggers `fetch(plugin.serviceBase + '/run'|'/lint')` with JSON body `{ code }`.
- Backend endpoints `/pluginpython/run` and `/pluginpython/lint` return JSON `{ output: ... }`.
- JS writes returned output text into the output panel.

## 5) Config dialog dataflow (showing incoming info in editor)
- Config JS entrypoint `configPluginPython(dtoString)` receives `PluginConfigDto`.
- It renders `dto.params['vars']` and `dto.params['help']` in the dialog.
- On config edits, it updates hidden config field and calls `dto.pluginDtoUri` (`/pluginpython/api/open/reloadplugindto`) with `configurationID`.
- Backend resolves state by `configurationID`, merges stored `questionDto` (including vars), and returns refreshed `PluginDto`.
- Config JS calls `initPluginPython(...)` again to re-render preview using updated data.

## 6) Reverse proxy path
- Nginx forwards `/pluginpython/*` to the plugin container, so browser calls to `/pluginpython/run` and `/pluginpython/lint` hit this service.


## 7) Dataset variables in config unit tests
- LeTTo sends the active question dataset in `questionDto` during `/open/setconfigurationdata`; the plugin stores it in the configuration state.
- The backend exposes a JSON-safe copy of `questionDto.vars`, `questionDto.cvars`, `questionDto.varsMaxima`, and `questionDto.mvars` as `dto.params.dataset` on the config DTO and refreshed plugin DTO.
- `PythonConfigScript.js` forwards that dataset in `questionConfigDto.dataset` when Run/Check/Score requests are sent from the configuration dialog.
- The execution backend converts `questionConfigDto.dataset` into a generated Jobe-side `dataset.py` module. Unit tests can use `from dataset import VARS, CVARS, MVARS, DATASET` or import individual plain `vars` names directly, for example `from dataset import answer`.
