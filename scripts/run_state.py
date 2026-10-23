"""Read Airflow run state by run_id (Airflow 2.10 dags state expects a date)."""
import sys
from airflow.models import DagRun
from airflow.utils.session import create_session
with create_session() as session:
 run=session.query(DagRun).filter(DagRun.dag_id=='agri_prices_etl',DagRun.run_id==sys.argv[1]).one_or_none()
 print(run.state if run else 'not_found')
