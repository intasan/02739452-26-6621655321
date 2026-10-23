from __future__ import annotations
from datetime import datetime
import json
import os
from airflow.decorators import dag, task, task_group
from airflow.operators.python import BranchPythonOperator

@dag(dag_id="agri_prices_etl",start_date=datetime(2026,10,1),
     schedule_interval=None,catchup=False,tags=["02739452","agriculture"])
def pipeline():
    @task_group(group_id="parallel_sources")
    def sources():
        @task
        def fetch(source):
            from collectors import collect_talaadthai,collect_dit,collect_nabc
            try:
                rows={"talaadthai":collect_talaadthai,"dit":collect_dit,"nabc":collect_nabc}[source]()
                return {"source":source,"ok":True,"rows":rows,"error":None}
            except Exception as e:
                # One source failure must not prevent processing of remaining sources.
                return {"source":source,"ok":False,"rows":[],"error":str(e)}
        names=[s.strip() for s in os.getenv('AGRI_SOURCES','dit,nabc,talaadthai').split(',') if s.strip()]
        if not names or len(names)!=len(set(names)) or any(s not in {'dit','nabc','talaadthai'} for s in names):
            raise ValueError('AGRI_SOURCES must list distinct dit,nabc,talaadthai sources')
        return [fetch.override(task_id=f"fetch_{s}")(s) for s in names]

    @task
    def merge_and_validate(parts):
        from quality import merge_and_validate as validate
        from airflow.operators.python import get_current_context
        result=validate(parts)
        result['source_status']={p['source']:{'ok':p['ok'],'extracted_rows':len(p['rows']),'error':p['error']} for p in parts}
        result['input_mode']=get_current_context()['dag_run'].conf.get('input_mode','live')
        return result

    def branch(**context):
        result=context["ti"].xcom_pull(task_ids="merge_and_validate")
        from quality import branch_target
        return branch_target(result)

    @task(task_id="load_prices")
    def load():
        import psycopg2
        from psycopg2.extras import execute_values
        from airflow.operators.python import get_current_context
        ti=get_current_context()["ti"]
        result=ti.xcom_pull(task_ids="merge_and_validate")
        rows=result["rows"]
        values=[tuple(r.get(k) for k in ("observation_key","source","source_record_id","product_name",
                "product_code","province","market_name","unit","price_min",
                "price_max","observed_at","measurement_type","source_url")) for r in rows]
        from contextlib import closing
        with closing(psycopg2.connect(os.environ["APP_DATABASE_URL"])) as conn, conn:
            with conn.cursor() as cur:
                execute_values(cur,"""
                  INSERT INTO agricultural_prices
                  (observation_key,source,source_record_id,product_name,product_code,province,market_name,
                   unit,price_min,price_max,observed_at,measurement_type,source_url)
                  VALUES %s ON CONFLICT (observation_key) DO UPDATE SET
                  source=EXCLUDED.source,source_record_id=EXCLUDED.source_record_id,
                  product_name=EXCLUDED.product_name,price_min=EXCLUDED.price_min,
                  price_max=EXCLUDED.price_max,ingested_at=NOW()""",values)
                cur.execute("""INSERT INTO pipeline_runs(run_id,loaded_rows,rejected_rows,status,details)
                  VALUES (%s,%s,%s,%s,%s) ON CONFLICT(run_id) DO UPDATE SET
                  loaded_rows=EXCLUDED.loaded_rows,rejected_rows=EXCLUDED.rejected_rows,
                  status=EXCLUDED.status,details=EXCLUDED.details""",(ti.run_id,len(rows),result["rejected"],
                    "partial" if result["errors"] else "success",json.dumps({k:v for k,v in result.items() if k!="rows"})))
        return len(rows)

    @task(task_id="no_valid_data")
    def empty():
        from airflow.exceptions import AirflowException
        raise AirflowException("No valid real data available; check source logs and configuration")

    results=merge_and_validate(sources())
    decision=BranchPythonOperator(task_id="quality_branch",python_callable=branch)
    results >> decision >> [load(),empty()]

pipeline()
