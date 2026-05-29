@echo off
for /f %%i in ('git rev-parse --short=12 HEAD') do set PLUGIN_BUILD_HASH=%%i
docker build --build-arg PLUGIN_BUILD_HASH=%PLUGIN_BUILD_HASH% -t lettohub/letto-plugin-python:latest -f Dockerfile .
docker compose -f /opt/letto/docker/compose/letto/docker-service-pluginpython.yml down
copy yml\docker-service-pluginpython.yml \opt\letto\docker\compose\letto\
docker compose -f /opt/letto/docker/compose/letto/docker-service-pluginpython.yml up -d
