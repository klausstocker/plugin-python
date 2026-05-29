@echo off
setlocal
set "PLUGIN_BUILD_HASH="
for /f "delims=" %%i in ('git rev-parse --verify --short=12 HEAD 2^>nul') do set "PLUGIN_BUILD_HASH=%%i"
if not defined PLUGIN_BUILD_HASH if exist revision.txt set /p PLUGIN_BUILD_HASH=<revision.txt
if not defined PLUGIN_BUILD_HASH set "PLUGIN_BUILD_HASH=unknown"
echo Building letto-plugin-python with PLUGIN_BUILD_HASH=%PLUGIN_BUILD_HASH%
docker build --build-arg "PLUGIN_BUILD_HASH=%PLUGIN_BUILD_HASH%" -t lettohub/letto-plugin-python:latest -f Dockerfile .
docker compose -f /opt/letto/docker/compose/letto/docker-service-pluginpython.yml down
copy yml\docker-service-pluginpython.yml \opt\letto\docker\compose\letto\
docker compose -f /opt/letto/docker/compose/letto/docker-service-pluginpython.yml up -d
