.PHONY: lint format

lint:
	ruff check axiomai --fix
	mypy axiomai

format:
	isort axiomai
	ruff format axiomai
