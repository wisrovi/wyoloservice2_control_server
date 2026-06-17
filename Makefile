start: ## Levanta la interfaz de monitoreo Gradio
	docker-compose -f docker-compose.api.yaml up -d --build

stop: ## Detiene el plano de control
	docker-compose -f docker-compose.api.yaml down

logs: ## Muestra los logs del plano de control
	docker-compose -f docker-compose.api.yaml logs -f

clean: ## Limpia contenedores detenidos y redes huérfanas
	docker system prune -f
	docker network prune -f

