@echo off
setlocal
set "PLUGIN_BUILD_HASH="
set "SCRIPT_DIR=%~dp0"
if exist "%SCRIPT_DIR%.git" (
    for /f "usebackq delims=" %%i in (`git -C "%SCRIPT_DIR%." log -1 --format^=%%h 2^>nul`) do set "PLUGIN_BUILD_HASH=%%i"
)
if not defined PLUGIN_BUILD_HASH if exist "%SCRIPT_DIR%revision.txt" set /p PLUGIN_BUILD_HASH=<"%SCRIPT_DIR%revision.txt"
if not defined PLUGIN_BUILD_HASH set "PLUGIN_BUILD_HASH=unknown"
echo Building letto-plugin-python with PLUGIN_BUILD_HASH=%PLUGIN_BUILD_HASH%
docker build --build-arg "PLUGIN_BUILD_HASH=%PLUGIN_BUILD_HASH%" -t lettohub/letto-plugin-python:latest -f "%SCRIPT_DIR%Dockerfile" "%SCRIPT_DIR%."
docker compose -f /opt/letto/docker/compose/letto/docker-service-pluginpython.yml down
copy "%SCRIPT_DIR%yml\docker-service-pluginpython.yml" \opt\letto\docker\compose\letto\
docker compose -f /opt/letto/docker/compose/letto/docker-service-pluginpython.yml up -d
