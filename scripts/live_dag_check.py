"""Two real network DAG runs against the configured PostgreSQL database."""
import os,sys,pathlib,json
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'dags'))
from airflow.models import DagBag
import pendulum,psycopg2
from contextlib import closing
b=DagBag(str(ROOT/'dags'),include_examples=False);assert not b.import_errors,b.import_errors
d=b.dags['agri_prices_etl'];results=[]
for number in (1,2):
 run=d.test(execution_date=pendulum.now('UTC').subtract(seconds=1),run_conf={'input_mode':'live','scenario':f'live_run_{number}'})
 with closing(psycopg2.connect(os.environ['APP_DATABASE_URL'])) as c,c:
  with c.cursor() as q:
   q.execute('SELECT count(*) FROM agricultural_prices');count=q.fetchone()[0]
   q.execute('SELECT loaded_rows,status,details FROM pipeline_runs WHERE run_id=%s',(run.run_id,));audit=q.fetchone()
 results.append({'run':number,'run_id':run.run_id,'state':str(run.state),'persisted_rows':count,'audit':audit})
 assert run.state=='success',str(run.state)
(ROOT/'evidence/live-dag-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2,default=str))
assert results[0]['persisted_rows']==results[1]['persisted_rows'],'New source observations or idempotency issue: inspect raw data'
print(json.dumps(results,ensure_ascii=False,indent=2,default=str))

from airflow.models.serialized_dag import SerializedDagModel
from airflow.utils.session import create_session
with create_session() as session:
 d.sync_to_db(session=session)
 SerializedDagModel.write_dag(d,session=session)
