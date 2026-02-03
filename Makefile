.PHONY: lint format up-prod grafana

lint:
	ruff check axiomai --fix
	mypy axiomai

format:
	isort axiomai
	ruff format axiomai

up-prod:
	docker compose -f docker-compose.prod.yaml pull
	docker compose -f docker-compose.prod.yaml up -d

grafana:
	docker compose -f docker-compose.grafana.yaml pull
	docker compose -f docker-compose.grafana.yaml up -d
