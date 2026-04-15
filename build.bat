docker build -t lettohub/letto-plugin-demopython:latest -f Dockerfile .
docker compose -f /opt/letto/docker/compose/letto/docker-service-plugindemopython.yml down
cp yml/docker-service-plugindemopython.yml /opt/letto/docker/compose/letto/
docker compose -f /opt/letto/docker/compose/letto/docker-service-plugindemopython.yml up -d