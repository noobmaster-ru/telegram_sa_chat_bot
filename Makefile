.PHONY:
all:
	docker compose down
	rm -rf pgdata_dev
	docker compose up -d --build
	docker compose run --rm clients_bot uv run python -m alembic upgrade head
	docker compose logs -f