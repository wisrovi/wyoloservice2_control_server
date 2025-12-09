# --------------------------------------------------
# Docker-in-Docker
# --------------------------------------------------

start_dind:
	docker-compose -f docker-compose.dind.yaml up -d --build

	docker-compose -f docker-compose.dind.yaml exec dind_environment sh -c "cd /app && docker-compose up -d"
	docker-compose -f docker-compose.dind.yaml exec dind_media sh -c "cd /app && docker-compose up -d"
	docker-compose -f docker-compose.dind.yaml exec dind_api sh -c "cd /app && docker-compose up -d"

stop_dind:
	docker-compose -f docker-compose.dind.yaml down

build_dind:
	docker-compose -f docker-compose.dind.yaml build

into_environment:
	docker-compose -f docker-compose.dind.yaml exec dind_environment sh

into_media:
	docker-compose -f docker-compose.dind.yaml exec dind_media sh

into_api:
	docker-compose -f docker-compose.dind.yaml exec dind_api sh

logs_environment:
	docker-compose -f docker-compose.dind.yaml exec dind_environment sh -c "cd /app && docker-compose logs -f"

logs_media:
	docker-compose -f docker-compose.dind.yaml exec dind_media sh -c "cd /app && docker-compose logs -f"

logs_api:
	docker-compose -f docker-compose.dind.yaml exec dind_api sh -c "cd /app && docker-compose logs -f"

restart_environment:
	docker-compose -f docker-compose.dind.yaml exec dind_environment sh -c "cd /app && docker-compose restart"

restart_media:
	docker-compose -f docker-compose.dind.yaml exec dind_media sh -c "cd /app && docker-compose restart"

restart_api:
	docker-compose -f docker-compose.dind.yaml exec dind_api sh -c "cd


# --------------------------------------------------
# Basic
# --------------------------------------------------
start_basic:
	docker-compose -f docker-compose.basic.yaml --env-file config/control_host.env --compatibility up -d --build  --force-recreate --no-deps  --pull always

stop_basic:
	docker-compose -f docker-compose.basic.yaml --env-file config/control_host.env down

create_network:
	docker network create wyoloservice_network || true

start_api_only:
	docker-compose -f docker-compose.basic.yaml --env-file config/control_host.env --compatibility up -d --build --force-recreate --no-deps --pull always neuroforge-api

.PHONY: start stop into_environment into_media into_api logs_environment logs_media logs_api restart_environment restart_media restart_api

