# Минимальный docker-compose для нашего конфига

Этот пример `docker-compose.yml` рассчитан на уже настроенный файл `config/settings.ini`.
Он не меняет содержимое конфига, а только подключает его в контейнер, собранный из текущего
репозитория (образ `netbox-sync:local`). Скрипт `scripts/docker_entrypoint.py` внутри образа
использует переменную `NBS_RUN_INTERVAL`, чтобы перезапускать синхронизацию через заданный интервал.
Благодаря нормализации аргументов entrypoint не требуется никаких правок кода или Dockerfile:
`docker compose` передаёт команду как есть (`-c /app/settings.ini`), без лишних `sh -c`, так что
достаточно подготовить конфигурацию и запустить сервис.

```yaml
services:
  netbox-sync:
    image: netbox-sync:local
    container_name: netbox-sync
    restart: unless-stopped
    environment:
      NBS_NETBOX_API_TOKEN: ${NBS_NETBOX_API_TOKEN}
      NBS_RUN_INTERVAL: 3600   # запускаем каждые 3600 секунд (1 час)
    volumes:
      - ./config/settings.ini:/app/settings.ini:ro
    command: ["-c", "/app/settings.ini"]
```

## Как использовать
1. Соберите образ: `docker build -t netbox-sync:local .` или `docker compose build` из корня проекта.
2. Убедитесь, что рядом с `docker-compose.yml` существует файл `config/settings.ini`.
3. Создайте `.env` с переменной `NBS_NETBOX_API_TOKEN`, чтобы не хранить токен в открытом виде.
4. Запустите сервис: `docker compose up -d`.
5. Посмотрите логи: `docker compose logs -f`.

Если нужно выполнить разовый «сухой» прогон, используйте `docker compose run --rm netbox-sync -n -c /app/settings.ini`.
