# AxiomAI

## Deployment

### Подготовка окружения

1. Скопировать .env ```cp .env.dist .env```
2. Добавить файл `sunny-might-477012-c4-04c66c69a92f.json`

### Запуск приложения

Запуск сервисов:

```bash
make up-prod
```

### Запуск Grafana (мониторинг)

Запуск стека мониторинга:

```bash
make grafana
```

Grafana доступна по адресу: http://localhost:3001
