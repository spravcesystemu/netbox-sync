
# NetBox-Sync

> [!CAUTION]
> **Maintainer wanted - sunsetting this repository by 31.10.2025 [#474](https://github.com/bb-Ricardo/netbox-sync/issues/474)**

This is a tool to sync data from different sources to a NetBox instance.

Available source types:
* VMware vCenter Server
* [bb-ricardo/check_redfish](https://github.com/bb-Ricardo/check_redfish) inventory files

**IMPORTANT: READ INSTRUCTIONS CAREFULLY BEFORE RUNNING THIS PROGRAM**

## Thanks
A BIG thank-you goes out to [Raymond Beaudoin](https://github.com/synackray) for creating
[vcenter-netbox-sync](https://github.com/synackray/vcenter-netbox-sync) which served as source of a lot
of ideas for this project.

## Principles

> copied from [Raymond Beaudoin](https://github.com/synackray)

The [NetBox documentation](https://netbox.readthedocs.io/en/stable/#serve-as-a-source-of-truth) makes it clear
the tool is intended to act as a "Source of Truth". The automated import of live network state is
strongly discouraged. While this is sound logic we've aimed to provide a middle-ground
solution for those who desire the functionality.

All objects collected from vCenter have a "lifecycle". Upon import, for supported object types,
they are tagged `NetBox-synced` to note their origin and distinguish them from other objects.
Using this tagging system also allows for the orphaning of objects which are no longer detected in vCenter.
This ensures stale objects are removed from NetBox keeping an accurate current state.

## Requirements
### Software
* python >= 3.6
* packaging
* urllib3==2.2.1
* wheel
* requests==2.31.0
* pyvmomi==8.0.2.0.1
* aiodns==3.0.0
* pyyaml==6.0.1

### Environment
* NetBox >= 4.2.2
#### Source: VMWare (if used)
* VMWare vCenter >= 6.0
#### Source: check_redfish (if used)
* check_redfish >= 1.2.0

# Installing
* here we assume we install in ```/opt```

## RedHat based OS
* on RedHat/CentOS 7 you need to install python3.6 and pip from EPEL first
* on RedHat/CentOS 8 systems the package name changed to `python3-pip`
```shell
yum install python36-pip
```

## Ubuntu 18.04 & 20.04 && 22.04
```shell
apt-get update && apt-get install python3-venv
```

## Clone repo and install dependencies
* If you need to use python 3.6 then you would need `requirements_3.6.txt` to install requirements
* download and setup of virtual environment
```shell
cd /opt
git clone https://github.com/bb-Ricardo/netbox-sync.git
cd netbox-sync
python3 -m venv .venv
. .venv/bin/activate
pip3 install --upgrade pip || pip install --upgrade pip
pip3 install wheel || pip install wheel
pip3 install -r requirements.txt || pip install -r requirements.txt
```

### VMware tag sync (if necessary)
The `vsphere-automation-sdk` must be installed if tags should be synced from vCenter to NetBox
* assuming we are still in an activated virtual env
```shell
pip install --upgrade git+https://github.com/vmware/vsphere-automation-sdk-python.git
```

## NetBox API token
In order to updated data in NetBox you need a NetBox API token.
* API token with all permissions (read, write) except:
  * auth
  * secrets
  * users

A short description can be found [here](https://docs.netbox.dev/en/stable/integrations/rest-api/#authentication)

# Запуск в Docker

Ниже приведён пример, как полностью собрать образ и запустить синхронизатор в Docker.

1. Склонируйте репозиторий и перейдите в его директорию:

   ```bash
   git clone https://github.com/bb-Ricardo/netbox-sync.git
   cd netbox-sync
   ```

2. Соберите локальный образ (в примере тег `netbox-sync:local`):

   ```bash
   docker build -t netbox-sync:local .
   ```

3. Подготовьте каталог с конфигурацией и сгенерируйте стартовый файл настроек внутри контейнера:

   ```bash
   mkdir -p ./config
   docker run --rm \
     -v "$(pwd)/config:/config" \
     netbox-sync:local -g -c /config/settings.ini
   ```


   Если при генерации появляется ошибка `permission denied /config/settings.ini`, выдайте каталогу права на запись для пользователя
   с UID 1000 (именно под ним работает контейнер):

   ```bash
   sudo chown -R 1000:1000 ./config
   # или откройте права на запись для всех пользователей
   sudo chmod -R a+rwX ./config
   ```

4. Запустите синхронизацию. Конфиг монтируем только для чтения, при необходимости добавьте переменные окружения с токенами и другими секретами:

   ```bash
   docker run --rm \
     -v "$(pwd)/config/settings.ini:/app/settings.ini:ro" \
     -e NBS_NETBOX_API_TOKEN="<ваш токен>" \
     netbox-sync:local -c /app/settings.ini
   ```

   Переменные окружения повторяют структуру секций из `settings.ini` и записываются в формате `NBS_<СЕКЦИЯ>_<ОПЦИЯ>`, например `NBS_NETBOX_HOST_FQDN`. Значения из переменных окружения перекрывают конфиг.

5. Для пробного запуска без изменений в NetBox добавьте ключ `-n`:

   ```bash
   docker run --rm \
     -v "$(pwd)/config/settings.ini:/app/settings.ini:ro" \
     -e NBS_NETBOX_API_TOKEN="<ваш токен>" \
     netbox-sync:local -n -c /app/settings.ini
   ```

### Автоматический запуск по расписанию внутри контейнера

Если нужно, чтобы синхронизатор автоматически стартовал каждые N секунд,
задайте переменную окружения `NBS_RUN_INTERVAL`. Переменная обрабатывается
встроенным обёрточным скриптом `scripts/docker_entrypoint.py`, который идёт
вместе с образом и перезапускает `netbox-sync` по таймеру. Например, чтобы
запускать сканирование каждый час (3600 секунд):

```bash
docker run --rm \
  -v "$(pwd)/config/settings.ini:/app/settings.ini:ro" \
  -e NBS_NETBOX_API_TOKEN="<ваш токен>" \
  -e NBS_RUN_INTERVAL=3600 \
  netbox-sync:local -c /app/settings.ini
```

Контейнер выполнит `netbox-sync` сразу после запуска, затем будет ждать указанное
число секунд и повторять цикл, пока вы его не остановите (`docker stop` / `Ctrl+C`).
Если переменная `NBS_RUN_INTERVAL` не указана или установлена в ноль/отрицательное
значение, контейнер выполнит синхронизацию только один раз, как и прежде.

### Распространённые ошибки при запуске контейнера

* **`Name or service not known` / `Failed to resolve 'netbox.example.com'`.**

  Такие сообщения появляются, если в `settings.ini` оставлено значение по умолчанию `netbox.example.com`, а DNS на хосте не знает, куда его направить. Убедитесь, что в секции `[netbox]` прописан реальный адрес вашей инсталляции NetBox (например, `http://127.0.0.1:6666` или внутренний FQDN). Если NetBox доступен только по IP, просто укажите IP-адрес. При необходимости добавьте запись в `/etc/hosts` или передайте Docker параметр `--add-host netbox.example.com:<IP>`.

* **`permission denied /config/settings.ini`** при генерации конфига.

  См. рекомендации из шага 3 выше: выдайте каталогу `config` права на запись пользователю с UID 1000 или сделайте каталог доступным на запись всем пользователям.

## Запуск через docker compose

Если вы предпочитаете управлять синхронизатором через `docker compose`, в репозитории есть готовый файл `docker-compose.yml`, повторяющий логику одиночного запуска и поддержку переменной `NBS_RUN_INTERVAL` из обёртки `scripts/docker_entrypoint.py`.

1. **Соберите образ.** Выполните команду в каталоге репозитория:

   ```bash
   docker compose build
   ```

   Эта команда использует `Dockerfile` и тег `netbox-sync:local`, чтобы образ был доступен как для `docker compose`, так и для разовых запусков `docker run`.

2. **Подготовьте конфиг.** Как и в варианте с `docker run`, создайте каталог `config` и сгенерируйте `settings.ini`:

   ```bash
   mkdir -p ./config
   docker run --rm \
     -v "$(pwd)/config:/config" \
     netbox-sync:local -g -c /config/settings.ini
   ```

   Отредактируйте файл `config/settings.ini`, указав реальные параметры NetBox и источников.


   NBS_NETBOX_API_TOKEN=0123456789abcdef0123456789abcdef01234567
   NBS_RUN_INTERVAL=3600
   # Пример секции источника (индекс и ключи должны совпадать с вашим settings.ini)
   NBS_SOURCES_1_NAME=vcenter
   NBS_SOURCES_1_USERNAME=svc-sync
   NBS_SOURCES_1_PASSWORD=SuperSecretPassw0rd
   ```

   *`NBS_RUN_INTERVAL` задаёт периодичность повторного запуска в секундах. Значение `3600` соответствует одному запуску в час. Если переменную убрать или оставить `0`, контейнер отработает один раз и завершится.*

4. **Поднимите сервис:**

   ```bash
   docker compose up -d
   ```

   Команда поднимет контейнер `netbox-sync`, смонтирует `config/settings.ini` в `/app/settings.ini` и передаст параметры запуска `-c /app/settings.ini`. Благодаря переменной `NBS_RUN_INTERVAL` entrypoint будет повторно запускать синхронизацию с заданным интервалом.

5. **Проверяйте логи:**

   ```bash
   docker compose logs -f
   ```

6. **Остановка контейнера:**

   ```bash
   docker compose down
   ```

   При остановке данные конфигурации сохраняются в каталоге `config`. Чтобы перезапустить синхронизатор вручную вне расписания, используйте `docker compose run --rm netbox-sync -n -c /app/settings.ini`.

## Полный сценарий запуска в `/opt/netbox-sync-v4/`

Ниже — пример, как развернуть `netbox-sync` «под ключ» в отдельной директории `/opt/netbox-sync-v4/`, используя стандартный `docker-compose.yml` из репозитория и обёртку `scripts/docker_entrypoint.py`, которая поддерживает автоматический перезапуск по переменной `NBS_RUN_INTERVAL`.

1. **Клонируйте репозиторий в нужную папку.**

   ```bash
   sudo git clone https://github.com/bb-Ricardo/netbox-sync.git /opt/netbox-sync-v4
   sudo chown -R "$(id -u)":"$(id -g)" /opt/netbox-sync-v4
   cd /opt/netbox-sync-v4
   ```

   Если каталог уже создан, просто скопируйте в него содержимое репозитория и убедитесь, что у вашего пользователя есть права на запись.

2. **Соберите локальный образ.**

   ```bash
   docker compose build
   ```

   Команда использует `Dockerfile` из репозитория и создаёт образ `netbox-sync:local`, который далее применяется как в `docker compose`, так и при ручных запусках `docker run`.

3. **Подготовьте каталог `config` и сгенерируйте стартовый `settings.ini`.**

   ```bash
   mkdir -p ./config
   docker run --rm \
     -v "$(pwd)/config:/config" \
     netbox-sync:local -g -c /config/settings.ini
   ```

   Отредактируйте `config/settings.ini`, указав реальные параметры NetBox и источников данных. Если при генерации возникла ошибка `permission denied /config/settings.ini`, выдайте каталогу права на запись для пользователя с UID 1000: `sudo chown -R 1000:1000 ./config`.

4. **Создайте `.env` рядом с `docker-compose.yml`, чтобы не хранить секреты в открытом виде.**

   ```bash
   cat > .env <<'EOF'

   NBS_NETBOX_API_TOKEN=0123456789abcdef0123456789abcdef01234567
   NBS_RUN_INTERVAL=3600
   # Если в settings.ini описан источник с индексом 1, можно передать пароль через переменные
   NBS_SOURCES_1_NAME=vcenter
   NBS_SOURCES_1_USERNAME=svc-sync
   NBS_SOURCES_1_PASSWORD=SuperSecretPassw0rd
   EOF
   ```

   Переменная `NBS_RUN_INTERVAL` задаёт периодичность повторного запуска `netbox-sync` (в секундах). Значение `3600` означает один запуск в час. За обработку интервала отвечает скрипт `scripts/docker_entrypoint.py`, являющийся entrypoint-обёрткой контейнера.

5. **Запустите синхронизацию в фоне.**

   ```bash
   docker compose up -d
   ```

   Контейнер автоматически примонтирует `config/settings.ini` в `/app/settings.ini` и выполнит `netbox-sync -c /app/settings.ini`. После каждого завершения процесса entrypoint заснёт на `NBS_RUN_INTERVAL` секунд и повторит цикл, пока сервис не будет остановлен.

6. **Следите за логами и проводите пробные запуски.**

   ```bash
   docker compose logs -f
   docker compose run --rm netbox-sync -n -c /app/settings.ini
   ```

   Команда с флагом `-n` выполняет «сухой» прогон без изменений в NetBox — полезно для проверки конфигурации перед боевым запуском.

7. **Остановите сервис при необходимости.**

   ```bash
   docker compose down
   ```

   Каталог `config/` сохраняет настройки между перезапусками. Чтобы полностью удалить временные данные контейнера, можно добавить флаг `--volumes`.

## Подключение к уже работающему NetBox на порту 8000

Если NetBox уже запущен в отдельном контейнере и доступен на порту `8000`,
например каталог развёрнутого проекта расположен в `/opt/netbox-sync`,
достаточно направить `netbox-sync` на этот инстанс. Ниже пример последовательности
действий, предполагающий, что синхронизатор собирается и запускается в отдельном
каталоге (например, в `/opt/netbox-sync-v3/`).

1. Убедитесь, что NetBox отвечает на запросы API. С хоста, где будет стартовать
   `netbox-sync`, выполните:

   ```bash
   curl http://127.0.0.1:8000/api/
   ```

   Если NetBox опубликован не на localhost, укажите фактическое имя/адрес.

2. Сгенерируйте конфигурацию для синхронизатора (см. раздел «Запуск в Docker»)
   и пропишите параметры существующего NetBox. Минимальный блок в `settings.ini`
   будет выглядеть так:

   ```ini
   [netbox]
   host_fqdn = http://127.0.0.1:8000
   api_token = <API-токен из вашего NetBox>
   verify_ssl = false
   ```

   *Если NetBox обслуживается по HTTPS, замените схему на `https://` и при
   необходимости включите проверку сертификата (`verify_ssl = true`).*

3. Запустите контейнер `netbox-sync`, смонтировав конфиг. Если NetBox и
   синхронизатор находятся на одной Docker-сети, добавьте флаг `--network` с
   нужным значением, иначе обращайтесь к NetBox по IP/имени хоста, которое
   доступно из контейнера:

   ```bash
   docker run --rm \
     -v "/opt/netbox-sync-v3/config/settings.ini:/app/settings.ini:ro" \
     -e NBS_NETBOX_API_TOKEN="<API-токен>" \
     netbox-sync:local -c /app/settings.ini
   ```

   При первом запуске целесообразно использовать ключ `-n`, чтобы убедиться,
   что запросы к NetBox проходят без ошибок.

Если при запуске появляется ошибка `Name or service not known`, проверьте,
что указанное имя NetBox резолвится внутри контейнера. Можно добавить опцию
`--add-host netbox.local:<IP>` или воспользоваться адресом `http://<IP>:8000`.

## Пример тестового стенда NetBox на порту 6666

Если в вашей инфраструктуре уже работает основная инсталляция NetBox, а для отладки `netbox-sync` требуется отдельный тестовый экземпляр, можно развернуть его рядом в Docker, выделив отдельный проект и порт. Ниже приведён пошаговый сценарий; в примере все файлы тестового стенда и `netbox-sync` располагаются в каталоге `/opt/netbox-sync-v3/`.

1. Подготовьте окружение и директорию проекта на хосте (предполагается, что Docker и docker compose уже установлены):

   ```bash
   sudo mkdir -p /opt/netbox-sync-v3
   sudo chown "$(id -u)":"$(id -g)" /opt/netbox-sync-v3
   cd /opt/netbox-sync-v3
   ```

2. Склонируйте официальный репозиторий [`netbox-docker`](https://github.com/netbox-community/netbox-docker) в подкаталог, чтобы иметь docker-compose манифесты:

   ```bash
   git clone https://github.com/netbox-community/netbox-docker.git
   cd netbox-docker
   ```

3. Скопируйте пример файла окружения и настройте отдельное имя проекта и порт 6666 для HTTP-интерфейса. Дополнительно укажите API-токен суперпользователя, который пригодится для тестов (его можно сменить после первого входа):

   ```bash
   cp env/netbox-docker.env .env
   cat >> .env <<'EOF'
   COMPOSE_PROJECT_NAME=netbox-sync-v3
   HTTP_PORT=6666
   SUPERUSER_API_TOKEN=0123456789abcdef0123456789abcdef01234567
   EOF
   ```

   > При необходимости добавьте в `.env` переменную `ALLOWED_HOSTS=*`, если NetBox нужно открыть извне.

4. Запустите тестовый стенд в фоне. Новый проект не пересечётся с боевым NetBox, потому что у него собственный `COMPOSE_PROJECT_NAME`, поэтому и имена контейнеров/томов будут отличаться:

   ```bash
   docker compose pull
   docker compose up -d
   ```

   После завершения инициализации панель NetBox станет доступна на `http://<адрес_хоста>:6666`. Стандартные учётные данные: `admin` / `admin`.

5. Сгенерируйте конфиг `netbox-sync` для нового стенда в каталоге `/opt/netbox-sync-v3` (можно использовать уже собранный образ `netbox-sync:local`, см. предыдущий раздел):

   ```bash
   cd /opt/netbox-sync-v3
   mkdir -p config
   docker run --rm \
     -v "$(pwd)/config:/config" \
     netbox-sync:local -g -c /config/settings.ini
   ```

6. Отредактируйте `config/settings.ini`, прописав адрес тестового NetBox и сгенерированный API-токен. Для NetBox, поднятого в docker compose, FQDN по умолчанию — IP хоста с портом 6666:

   ```ini
   [netbox]
   host_fqdn = http://127.0.0.1:6666
   api_token = 0123456789abcdef0123456789abcdef01234567
   verify_ssl = false
   ```

   > В боевой среде лучше включить TLS и задать `verify_ssl = true`.

7. Запустите синхронизацию против тестового стенда (сначала в режиме `-n`, чтобы убедиться, что запросы проходят корректно):

   ```bash
   docker run --rm \
     -v "/opt/netbox-sync-v3/config/settings.ini:/app/settings.ini:ro" \
     netbox-sync:local -n -c /app/settings.ini
   ```

   При необходимости добавьте переменные окружения `NBS_*`, чтобы передать секреты без сохранения в файл.

   Если контейнер сообщает `permission denied /config/settings.ini` при генерации или обновлении конфига, убедитесь, что каталог
   `/opt/netbox-sync-v3/config` доступен на запись пользователю с UID 1000:

   ```bash
   sudo chown -R 1000:1000 /opt/netbox-sync-v3/config
   sudo chmod -R u+rwX /opt/netbox-sync-v3/config
   ```

8. Чтобы остановить тестовый стенд NetBox, выполните:

   ```bash
   cd /opt/netbox-sync-v3/netbox-docker
   docker compose down
   ```

   Команда остановит контейнеры, но сохранит данные в томах. Для полного удаления (включая БД) добавьте флаг `--volumes`.

# Running the script

```
usage: netbox-sync.py [-h] [-c settings.ini [settings.ini ...]] [-g]
                      [-l {DEBUG3,DEBUG2,DEBUG,INFO,WARNING,ERROR}] [-n] [-p]

Sync objects from various sources to NetBox

Version: 1.9.0 (2025-10-21)
Project URL: https://github.com/bb-ricardo/netbox-sync

options:
  -h, --help            show this help message and exit
  -c settings.ini [settings.ini ...], --config settings.ini [settings.ini ...]
                        points to the config file to read config data from
                        which is not installed under the default path
                        './settings.ini'
  -g, --generate_config
                        generates default config file.
  -l {DEBUG3,DEBUG2,DEBUG,INFO,WARNING,ERROR}, --log_level {DEBUG3,DEBUG2,DEBUG,INFO,WARNING,ERROR}
                        set log level (overrides config)
  -n, --dry_run         Operate as usual but don't change anything in NetBox.
                        Great if you want to test and see what would be
                        changed.
  -p, --purge           Remove (almost) all synced objects which were create
                        by this script. This is helpful if you want to start
                        fresh or stop using this script.
```

## TESTING
It is recommended to set log level to `DEBUG2` this way the program should tell you what is happening and why.
Also use the dry run option `-n` at the beginning to avoid changes directly in NetBox.

## Configuration
There are two ways to define configuration. Any combination of config file(s) and environment variables is possible.
* config files (the [default config](https://github.com/bb-Ricardo/netbox-sync/blob/main/settings-example.ini) file name is set to `./settings.ini`.)
* environment variables

The config from the environment variables will have precedence over the config file definitions.

### Config files
Following config file types are supported:
* ini
* yaml

There is also more than one config file permitted. Example (config file names are also just examples):
```bash
/opt/netbox-sync/netbox-sync.py -c common.ini all-sources.yaml additional-config.yaml
```

All files are parsed in order of the definition and options will overwrite the same options if defined in a
previous config file.

To get config file examples which include descriptions and all default values, the `-g` can be used:
```bash
# this will create an ini example
/opt/netbox-sync/netbox-sync.py -g -c settings-example.ini

# and this will create an example config file in yaml format
/opt/netbox-sync/netbox-sync.py -g -c settings-example.yaml 
```

### Environment variables
Each setting which can be defined in a config file can also be defined using an environment variable.

The prefix for all environment variables to be used in netbox-sync is: `NBS`

For configuration in the `common` and `netbox` section a variable is defined like this
```
<PREFIX>_<SECTION_NAME>_<CONFIG_OPTION_KEY>=value
```

Following example represents the same configuration:
```yaml
# yaml config example
common:
  log_level: DEBUG2
netbox:
  host_fqdn: netbox-host.example.com
  prune_enabled: true
```
```bash
# this variable definition is equal to the yaml config sample above
NBS_COMMON_LOG_LEVEL="DEBUG2"
NBS_netbox_host_fqdn="netbox-host.example.com"
NBS_NETBOX_PRUNE_ENABLED="true"
```

This way it is possible to expose for example the `NBS_NETBOX_API_KEY` only via an env variable.

The config definitions for `sources` need to be defined using an index. Following conditions apply:
* a single source needs to use the same index
* the index can be number or a name (but contain any special characters to support env var parsing)
* the source needs to be named with `_NAME` variable

Example of defining a source with config and environment variables.
```ini
; example for a source
[source/example-vcenter]
enabled = True
type = vmware
host_fqdn = vcenter.example.com
username = vcenter-readonly
```
```bash
# define the password on command line
# here we use '1' as index
NBS_SOURCE_1_NAME="example-vcenter"
NBS_SOURCE_1_PASSWORD="super-secret-and-not-saved-to-the-config-file"
NBS_SOURCE_1_custom_dns_servers="10.0.23.23, 10.0.42.42"
```

Even to just define one source variable like `NBS_SOURCE_1_PASSWORD` the `NBS_SOURCE_1_NAME` needs to be defined as
to associate to the according source definition.

## Cron job
In Order to sync all items regularly you can add a cron job like this one
```
 # NetBox Sync
 23 */2 * * *  /opt/netbox-sync/.venv/bin/python3 /opt/netbox-sync/netbox-sync.py >/dev/null 2>&1
```

## Docker

Run the application in a docker container. You can build it yourself or use the ones from docker hub.

Available here: [bbricardo/netbox-sync](https://hub.docker.com/r/bbricardo/netbox-sync)

* The application working directory is ```/app```
* Required to mount your ```settings.ini```

To build it by yourself just run:
```shell
docker build -t bbricardo/netbox-sync:latest .
```

To start the container just use:
```shell
docker run --rm -it -v $(pwd)/settings.ini:/app/settings.ini bbricardo/netbox-sync:latest
```

## Kubernetes

Run the containerized application in a kubernetes cluster

* Create a config map with the default settings
* Create a secret witch only contains the credentials needed
* Adjust the provided [cronjob resource](https://github.com/bb-Ricardo/netbox-sync/blob/main/k8s-netbox-sync-cronjob.yaml) to your needs
* Deploy the manifest to your k8s cluster and check the job is running

config example saved as `settings.yaml`
```yaml
netbox:
  host_fqdn: netbox.example.com

source:
  my-vcenter-example:
    type: vmware
    host_fqdn: vcenter.example.com
    permitted_subnets: 172.16.0.0/12, 10.0.0.0/8, 192.168.0.0/16, fd00::/8
    cluster_site_relation: Cluster_NYC = New York, Cluster_FFM.* = Frankfurt, Datacenter_TOKIO/.* = Tokio
```

secrets example saved as `secrets.yaml`
```yaml
netbox:
  api_token: XYZXYZXYZXYZXYZXYZXYZXYZ
source:
  my-vcenter-example:
    username: vcenter-readonly
    password: super-secret
```

Create resource in your k8s cluster
 ```shell
kubectl create configmap netbox-sync-config --from-file=settings.yaml
kubectl create secret generic netbox-sync-secrets --from-file=secrets.yaml
kubectl apply -f k8s-netbox-sync-cronjob.yaml
 ```

# How it works
**READ CAREFULLY**

## Basic structure
The program operates mainly like this
1. parsing and validating config
2. instantiating all sources and setting up connection to NetBox
3. read current data from NetBox
4. read data from all sources and add/update objects in memory
5. Update data in NetBox based on data from sources
6. Prune old objects

## NetBox connection
Request all current NetBox objects. Use caching whenever possible.
Objects must provide "last_updated" attribute to support caching for this object type.

Actually perform the request and retry x times if request times out.
Program will exit if all retries failed!

## Supported sources
Check out the documentations for the different sources
* [vmware](https://github.com/bb-Ricardo/netbox-sync/blob/main/docs/source_vmware.md)
* [check_redfish](https://github.com/bb-Ricardo/netbox-sync/blob/main/docs/source_check_redfish.md)

If you have multiple vCenter instances or check_redfish folders just add another source with the same type
in the **same** file.

Example:
```ini
[source/vcenter-BLN]

enabled = True
host_fqdn = vcenter1.berlin.example.com

[source/vcenter-NYC]

enabled = True
host_fqdn = vcenter2.new-york.example.com

[source/redfish-hardware]

type = check_redfish
inventory_file_path = /opt/redfish_inventory
```

If different sources overwrite the same attribute for ex. a host then the order of the sources should be considered.
The last source in order from top to bottom will prevail.

## Pruning
Prune objects in NetBox if they are no longer present in any source.
First they will be marked as Orphaned and after X (config option) days they will be
deleted from NetBox.

Objects subjected to pruning:
* devices
* VMs
* device interfaces
* VM interfaces
* IP addresses

All other objects created (i.e.: VLANs, cluster, manufacturers) will keep the
source tag but will not be deleted. Theses are "shared" objects might be used
by different NetBox objects

# License
>You can check out the full license [here](https://github.com/bb-Ricardo/netbox-sync/blob/main/LICENSE.txt)

This project is licensed under the terms of the **MIT** license.
