@echo off
setlocal EnableExtensions
pushd "%~dp0"
if errorlevel 1 exit /b 1

if not exist ".env.docker-local" (
    echo Missing .env.docker-local. See README.md for the local environment configuration. >&2
    goto failed
)

rem Shell variables override the env file, without changing production defaults.
set "PLUGIN_DEV_UI=true"
set "PLUGIN_REGISTER_ON_READY=false"

docker info >nul 2>&1
if errorlevel 1 (
    echo Docker is unavailable. Start Docker Desktop and try again. >&2
    goto failed
)
docker compose version >nul 2>&1
if errorlevel 1 goto failed

docker network inspect nw-letto >nul 2>&1
if errorlevel 1 (
    docker network create nw-letto
    if errorlevel 1 goto failed
)

rem Resolve relative volume paths from the repository, rather than yml/.
rem Use locally built images; do not replace them by pulling published images.
docker compose --project-directory "%CD%" --env-file .env.docker-local -f yml/docker-service-pluginpythoncpp.yml up -d --no-build --pull never pythoncppplugin jobe
if errorlevel 1 goto failed

echo Development containers started.
echo Dialog: http://localhost:8209/pluginpython/dev/config
echo C/C++ dialog: http://localhost:8209/plugincpp/dev/config
echo Resources: http://localhost:8209/pluginpython/dev/resources/plugins/Python/PythonConfigScript.js
popd
exit /b 0

:failed
popd
exit /b 1
