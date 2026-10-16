# Лабораторная работа №1: события CMS и бозон Хиггса

Скачиваем небольшие открытые CSV из CERN Open Data (данные CMS за 2011 и 2012 годы), читаем их на Python и сохраняем в три разных хранилища:

- **PostgreSQL** — таблица `ods.events`, по одному событию на строку; исходные поля хранятся в JSONB.
- **MongoDB** — коллекция `higgs.events`, по одному событию на документ.
- **MinIO** — шесть оригинальных файлов CSV, без изменений.

Airflow запускает три независимых DAG (по каналам 4μ, 4e, 2e2μ). Каждый DAG загружает CSV за оба года.

Это образовательная выборка реальных событий-кандидатов, а не полный набор данных столкновений и не доказательство распада Хиггса для каждой записи. Портал CERN не рекомендует её для полноценного физического анализа.

Источник: https://opendata.cern.ch/record/5200  
DOI: https://doi.org/10.7483/OPENDATA.CMS.YGG7.333M

## Запуск 

1. Распаковать архив в простую папку, например `C:\higgs_lab1`.
2. Открыть Docker Desktop.
3. Открыть PowerShell в папке с `docker-compose.yml`.
4. Выполнить:

```powershell
docker compose up -d --build
```

5. Проверить контейнеры:

```powershell
docker compose ps
```

6. Открыть http://localhost:8080
   - логин: `admin`
   - пароль: `admin`

Если сайт пока не открывается, проверьте логи:

```powershell
docker compose logs --tail=50 airflow-webserver
docker compose logs --tail=50 airflow-scheduler
```

В Airflow найти:

1. `higgs_4mu`
2. `higgs_4e`
3. `higgs_2e2mu`

Для каждого нажать **Trigger DAG**

Проверить, что `download_and_save` завершилась зелёным статусом `success`. При ошибке откройте DAG → задачу → **Logs**.

**Проверка PostgreSQL вручную:**

```powershell
docker compose exec postgres psql -U airflow -d airflow -c "SELECT channel, year, COUNT(*) FROM ods.events GROUP BY channel, year ORDER BY channel, year;"
```

**Проверка MongoDB вручную:**

```powershell
docker compose exec mongo mongosh --quiet --eval "db.getSiblingDB('higgs').events.countDocuments({})"
```

**Проверка файлов MinIO:** http://localhost:9001

- логин: `minioadmin`
- пароль: `minioadmin`
- бакет: `higgs-raw`
- должны быть папки `4mu`, `4e` и `2e2mu`, по два CSV на канал.


| Файл | Назначение |
|---|---|
| `docker-compose.yml` | Запускает все контейнеры |
| `Dockerfile` | Устанавливает Python-библиотеки в Airflow |
| `dags/higgs_4mu.py` | DAG с четырьмя мюонами |
| `dags/higgs_4e.py` | DAG с четырьмя электронами |
| `dags/higgs_2e2mu.py` | DAG с двумя электронами и двумя мюонами |
| `dags/etl_utils.py` | Общая простая функция загрузки |
| `check_results.py` | Проверяет, что данные попали во все хранилища |
| `ОТЧЁТ_ШАБЛОН.md` | Текст для отчёта после проверки запуска |
| `ПОДСКАЗКА_НА_ЗАЩИТУ.md` | Короткие определения и ответы |

## `load_channel()`

1. Подставляет название канала и год в адрес CERN Open Data.
2. Скачивает CSV с помощью `requests.get()`.
3. `csv.DictReader()` превращает строки CSV в словари Python (все исходные значения сохраняются как строки).
4. `psycopg2` сохраняет строки в PostgreSQL.
5. `pymongo` сохраняет те же записи в MongoDB.
6. `minio` сохраняет исходный CSV целиком как файл.

В PostgreSQL используется ключ `(channel, year, run, event)`, в MongoDB стабильный `_id`, а в MinIO постоянное имя файла. Поэтому **повторный запуск не создаёт копии тех же событий**.