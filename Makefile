.PHONY:
all:
	docker compose down
	rm -rf pgdata_dev
	docker compose up -d --build
	alembic upgrade head
	docker compose logs -f 
