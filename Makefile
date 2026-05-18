# Makefile for Celery ML Cluster - NeuralForgeAI

.PHONY: help build build-all up down worker-up worker-down test logs clean

# Variables - Rutas a los repositorios
CONTROL_SERVER = ./wyoloservice2_control_server
MANAGER = ./wyoloservice2_manager
INVOKER = ./wyoloservice2_invoker
EXECUTOR = ./wyoloservice2_worker/executor
NEURALFORGEAI = ./NeuralForgeAI

help: ## Muestra esta ayuda
	@echo ""
	@echo "NeuralForgeAI - Distributed YOLO Training Cluster"
	@echo ""
	@echo "Uso:"
	@echo "  make \033[36m<objetivo>\033[0m"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\n\033[1mObjetivos:\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } ' $(MAKEFILE_LIST)

##@ Build Images

build-control-server: ## Construye la imagen del Control Server (API + Gradio)
	docker build -t wisrovi/train_service:control_server_v1.0.0 $(CONTROL_SERVER)

build-manager: ## Construye la imagen del Manager (Optuna Orchestrator)
	docker build -t wisrovi/train_service/manager:orchestrator_v1.0.0 $(MANAGER)

build-invoker: ## Construye la imagen del Worker Invoker
	docker build -t wisrovi/train_service:worker_invoker_v1.0.0 $(INVOKER)

build-executor: ## Construye la imagen del Worker Executor (YOLO)
	docker build -t wisrovi/train_service:worker_executor_v1.0.0 $(EXECUTOR)

build-neuralforgeai: ## Construye la imagen de NeuralForgeAI (React)
	docker build -t wisrovi/neuralforgeai:v1.0.0 $(NEURALFORGEAI)

build-all: build-control-server build-manager build-invoker build-executor build-neuralforgeai ## Construye todas las imágenes

##@ Deployment

up: ## Levanta el plano de control (API + Manager + Redis + PostgreSQL)
	cd $(CONTROL_SERVER) && docker-compose up -d --build

down: ## Detiene el plano de control
	cd $(CONTROL_SERVER) && docker-compose down

worker-up: ## Levanta el Worker Invoker (para nodos GPU remotos)
	cd $(INVOKER) && docker-compose up -d --build

worker-down: ## Detiene el Worker Invoker
	cd $(INVOKER) && docker-compose down

##@ Push Images

push-control-server: ## Sube imagen del Control Server
	docker push wisrovi/train_service:control_server_v1.0.0

push-manager: ## Sube imagen del Manager
	docker push wisrovi/train_service/manager:orchestrator_v1.0.0

push-invoker: ## Sube imagen del Invoker
	docker push wisrovi/train_service:worker_invoker_v1.0.0

push-executor: ## Sube imagen del Executor
	docker push wisrovi/train_service:worker_executor_v1.0.0

push-neuralforgeai: ## Sube imagen de NeuralForgeAI
	docker push wisrovi/neuralforgeai:v1.0.0

push-all: push-control-server push-manager push-invoker push-executor push-neuralforgeai ## Sube todas las imágenes

##@ Development

test: ## Ejecuta los tests del sistema
	cd $(CONTROL_SERVER) && bash run_tests.sh

logs: ## Muestra los logs del plano de control
	cd $(CONTROL_SERVER) && docker-compose logs -f

worker-logs: ## Muestra los logs del Worker
	cd $(INVOKER) && docker-compose logs -f

clean: ## Limpia contenedores detenidos y redes huérfanas
	docker system prune -f
	docker network prune -f

##@ Status

ps: ## Muestra los contenedores en ejecución
	docker ps --filter "name=wyolo" --filter "name=neuralforgeai" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

logs-manager: ## Muestra logs del Manager
	docker logs $$(docker ps --filter "name=manager" -q)

logs-invoker: ## Muestra logs del Invoker
	docker logs $$(docker ps --filter "name=worker" -q)
