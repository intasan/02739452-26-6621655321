"""Actual live DAGs followed by isolated fault injection using captured real rows."""
import os,sys,json,pathlib,runpy,copy
from contextlib import closing
from decimal import Decimal
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'dags'))
import psycopg2,pendulum
import collectors
from airflow.models import DagBag
from quality import merge_and_validate
DSN=os.environ['APP_DATABASE_URL']
def query(sql):
 with closing(psycopg2.connect(DSN)) as c,c:
  with c.cursor() as q:q.execute(sql);return q.fetchall()
fields=('observation_key','source','source_record_id','product_name','product_code','province','market_name','unit','price_min','price_max','observed_at','measurement_type','source_url')
old={r[0]:r for r in query('SELECT '+','.join(fields)+' FROM agricultural_prices WHERE source IN (\'dit\',\'nabc\')')}
assert len(old)==354
runpy.run_path(str(ROOT/'scripts/live_dag_check.py'),run_name='__main__')
live=json.loads((ROOT/'evidence/live-dag-results.json').read_text())
assert all(x['state']=='success' for x in live)
assert live[0]['persisted_rows']==live[1]['persisted_rows']
now={r[0]:r for r in query('SELECT '+','.join(fields)+' FROM agricultural_prices')}
assert all(now[k]==v for k,v in old.items()),'Existing DIT/NABC record changed'
counts=dict(query('SELECT source,count(*) FROM agricultural_prices GROUP BY source'))
assert counts['dit']==82 and counts['nabc']==272 and counts['talaadthai']>0
b=DagBag(str(ROOT/'dags'),include_examples=False);assert not b.import_errors,b.import_errors;d=b.dags['agri_prices_etl']
fixture=json.loads((ROOT/'evidence/collection-three-sources.json').read_text())['sources']
for part in fixture:
 assert part['ok'],part['error']

def replay(mode):
 for part in fixture:
  def adapter(p=part):
   if p['source']=='talaadthai' and mode=='third_outage':raise ConnectionError('TEST ONLY: injected third-source outage')
   rows=copy.deepcopy(p['rows'])
   if p['source']=='talaadthai' and mode=='invalid_price':rows[0]['price_min']='-1'
   return rows
  setattr(collectors,'collect_'+part['source'],adapter)
 run=d.test(execution_date=pendulum.now('UTC').subtract(seconds=1),run_conf={'input_mode':'verified_snapshot_replay','scenario':mode})
 return str(run.state)
assert replay('third_outage')=='success'
assert replay('invalid_price')=='failed'
assert query('SELECT count(*) FROM agricultural_prices')[0][0]==len(now)
result={'engine':query('SELECT version()')[0][0],'before_two_sources':354,'after':len(now),'source_counts':counts,'old_354_rows_all_13_fields_unchanged':True,
 'live_dag_twice':'success','upsert_counts':[x['persisted_rows'] for x in live],'third_source_outage':'success; existing DIT/NABC continue','invalid_price_branch':'expected failed; no data changed','native_postgres16_docker_tested':False}
(ROOT/'evidence/third_source/integration-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
