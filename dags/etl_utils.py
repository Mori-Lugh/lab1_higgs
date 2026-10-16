"""Простая загрузка CSV из CERN в PostgreSQL, MongoDB и MinIO."""

import csv
import io
import json

import psycopg2
import requests
from minio import Minio
from minio.error import S3Error
from pymongo import MongoClient


def load_channel(channel):
    # По одному CSV за каждый год для выбранного канала.
    for year in [2011, 2012]:
        url = f"https://opendata.cern.ch/record/5200/files/{channel}_{year}.csv"

        # 1. Скачиваем исходный CSV.
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
        if not rows:
            raise ValueError(f"Нет данных в файле {channel}_{year}.csv")

        # 2. PostgreSQL: одна запись таблицы = одно событие.
        with psycopg2.connect(host="postgres", dbname="airflow",
                              user="airflow", password="airflow") as connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE SCHEMA IF NOT EXISTS ods")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ods.events (
                        channel TEXT,
                        year INTEGER,
                        run TEXT,
                        event TEXT,
                        data JSONB,
                        PRIMARY KEY (channel, year, run, event)
                    )
                """)
                for row in rows:
                    cursor.execute("""
                        INSERT INTO ods.events (channel, year, run, event, data)
                        VALUES (%s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (channel, year, run, event)
                        DO UPDATE SET data = EXCLUDED.data
                    """, (channel, year, row["Run"], row["Event"], json.dumps(row)))

        # 3. MongoDB: одно событие = один JSON-документ.
        with MongoClient("mongodb://mongo:27017/") as client:
            collection = client["higgs"]["events"]
            for row in rows:
                event_id = f"{channel}_{year}_{row['Run']}_{row['Event']}"
                collection.replace_one(
                    {"_id": event_id},
                    {"_id": event_id, "channel": channel, "year": year, "data": row},
                    upsert=True,
                )

        # 4. MinIO: сохраняем оригинальный файл CSV без изменений.
        minio = Minio("minio:9000", access_key="minioadmin",
                      secret_key="minioadmin", secure=False)
        if not minio.bucket_exists("higgs-raw"):
            try:
                minio.make_bucket("higgs-raw")
            except S3Error as error:
                # Два DAG могут одновременно попытаться создать один бакет.
                if error.code != "BucketAlreadyOwnedByYou":
                    raise
        minio.put_object(
            "higgs-raw", f"{channel}/{year}.csv",
            io.BytesIO(response.content), len(response.content),
            content_type="text/csv",
        )

        print(f"Загружено: {channel}, {year}, событий: {len(rows)}")
