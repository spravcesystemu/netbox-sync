# Запуск netbox-sync через Docker Compose (каталог `netbox-sync-v3/netbox-sync/`)

Ниже приведена пошаговая инструкция, как поднять контейнер `netbox-sync` в каталоге
`/opt/netbox-sync-v3/netbox-sync/`, используя стандартный `docker-compose.yml` из репозитория.

## 1. Подготовка каталога

```bash
sudo mkdir -p /opt/netbox-sync-v3
sudo chown -R "$(id -u)":"$(id -g)" /opt/netbox-sync-v3
cd /opt/netbox-sync-v3
```

Клонируйте репозиторий внутрь подкаталога `netbox-sync` (так вы получите структуру
`/opt/netbox-sync-v3/netbox-sync/`):

```bash
git clone https://github.com/bb-Ricardo/netbox-sync.git netbox-sync
cd netbox-sync
```

## 2. Сборка образа

Из корня проекта (`/opt/netbox-sync-v3/netbox-sync/`) выполните:

```bash
docker compose build
```

Команда соберёт локальный образ `netbox-sync:local`, который использует виртуальное
окружение Python и включает entrypoint `scripts/docker_entrypoint.py` для повторных запусков.

## 3. Генерация и подготовка `settings.ini`

Создайте каталог для конфигурации и сгенерируйте шаблон настроек:

```bash
mkdir -p ./config
docker run --rm \
  -v "$(pwd)/config:/config" \
  netbox-sync:local -g -c /config/settings.ini
```

Отредактируйте файл `config/settings.ini`, указав URL NetBox, токен API и источники данных.
Если появится ошибка `permission denied /config/settings.ini`, выдайте каталог `config` на запись
пользователю с UID 1000 (именно под ним работает контейнер):

```bash
sudo chown -R 1000:1000 ./config
sudo chmod -R u+rwX ./config
```

## 4. Создание `.env`

В каталоге `/opt/netbox-sync-v3/netbox-sync/` создайте файл `.env`, где будут храниться
секреты и параметры расписания:

```bash
cat > .env <<'EOT'
NBS_NETBOX_API_TOKEN=0123456789abcdef0123456789abcdef01234567
NBS_RUN_INTERVAL=3600
# Пример параметров источника (индекс 1). Замените на реальные значения:
# NBS_SOURCES_1_NAME=example-vcenter
# NBS_SOURCES_1_PASSWORD=SuperSecret
EOT
```

* `NBS_NETBOX_API_TOKEN` — токен NetBox, который можно удалить из `settings.ini`, чтобы не хранить его в файле.
* `NBS_RUN_INTERVAL` — интервал между запусками в секундах. `3600` означает один прогон в час.
  Если переменную не задавать или выставить `0`, синхронизатор завершится после одного запуска.
* Любые опции из `settings.ini` можно передать аналогично (`NBS_<СЕКЦИЯ>_<ОПЦИЯ>`).

## 5. Запуск Docker Compose

Чтобы запустить синхронизацию в фоне:

```bash
docker compose up -d
```

Контейнер автоматически примонтирует `config/settings.ini` в `/app/settings.ini` и будет
перезапускать `netbox-sync` с интервалом `NBS_RUN_INTERVAL`.

### Полезные команды

* Просмотр логов в реальном времени:
  ```bash
  docker compose logs -f netbox-sync
  ```
* Пробный «сухой» запуск без изменений в NetBox:
  ```bash
  docker compose run --rm netbox-sync -n -c /app/settings.ini
  ```
* Остановка сервиса и освобождение ресурсов:
  ```bash
  docker compose down
  ```
  Конфигурация в `config/` при этом сохраняется.

## 6. Обновление конфигурации или интервала

После изменения `config/settings.ini` или `.env` перезапустите контейнер:

```bash
docker compose up -d --force-recreate
```

Скрипт `scripts/docker_entrypoint.py` автоматически подхватит новый интервал и снова начнёт
циклически запускать `netbox-sync`.

## 7. Диагностика частых проблем

| Проблема | Решение |
| --- | --- |
| `permission denied /config/settings.ini` | Проверьте права каталога `config` (см. шаг 3). |
| `Failed to resolve 'netbox.example.com'` | Укажите реальный хост NetBox в `[netbox] host_fqdn`, либо добавьте `--add-host` или запись в `/etc/hosts`. |
| Контейнер завершился сразу после старта | Убедитесь, что `NBS_RUN_INTERVAL` > 0, если требуется периодический запуск. |

Следуя этим шагам, вы сможете запускать `netbox-sync` по расписанию из каталога
`/opt/netbox-sync-v3/netbox-sync/` без конфликтов с существующей инсталляцией NetBox.
