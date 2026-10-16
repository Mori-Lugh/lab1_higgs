"""Проверка данных после запуска всех трёх DAG."""

import psycopg2
from minio import Minio
from pymongo import MongoClient

with psycopg2.connect(host="postgres", dbname="airflow",
                      user="airflow", password="airflow") as db:
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT channel, year, COUNT(*)
            FROM ods.events
            GROUP BY channel, year
            ORDER BY channel, year
        """)
        print("PostgreSQL (канал, год, записей):")
        for row in cursor.fetchall():
            print(row)

with MongoClient("mongodb://mongo:27017/") as client:
    print("MongoDB (всего документов):", client["higgs"]["events"].count_documents({}))

minio = Minio("minio:9000", access_key="minioadmin",
              secret_key="minioadmin", secure=False)
print("MinIO (все сохранённые CSV):")
for item in minio.list_objects("higgs-raw", recursive=True):
    print(item.object_name, "—", item.size, "байт")
