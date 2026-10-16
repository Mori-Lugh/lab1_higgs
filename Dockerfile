FROM apache/airflow:2.10.5-python3.11

# Библиотеки для загрузки данных в три хранилища
RUN pip install --no-cache-dir requests==2.32.3 psycopg2-binary==2.9.10 pymongo==4.10.1 minio==7.2.15
