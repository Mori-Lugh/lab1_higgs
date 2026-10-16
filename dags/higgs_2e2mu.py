from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from etl_utils import load_channel

# DAG №3: события с двумя электронами и двумя мюонами.
with DAG("higgs_2e2mu", start_date=datetime(2025, 1, 1),
         schedule_interval=None, catchup=False, tags=["higgs", "lab1"]) as dag:
    PythonOperator(
        task_id="download_and_save",
        python_callable=load_channel,
        op_kwargs={"channel": "2e2mu"},
    )
