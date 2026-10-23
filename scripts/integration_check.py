"""Deterministic integration of existing real observations from three verified sources, never synthetic rows.
Run in an isolated database with APP_DATABASE_URL. Replays the saved source
responses through the actual Airflow DAG; it does not assert new live extraction.
Airflow metadata can use SQLite for dag.test; Docker uses PostgreSQL metadata.
"""
import sys,os,pathlib,json,copy,hashlib
from datetime import date
from decimal import Decimal
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'dags'))
import psycopg2
import collectors
from quality import merge_and_validate
from airflow.models import DagBag
from airflow.utils.dag_cycle_tester import check_cycle
import pendulum
BASE_TIME=pendulum.now("UTC").subtract(minutes=10)

DSN=os.environ['APP_DATABASE_URL']
snapshot=json.loads((ROOT/'evidence/collection-three-sources.json').read_text())
parts=snapshot['sources']
expected=merge_and_validate(parts)['rows']
assert len(expected)>=354
bag=DagBag(str(ROOT/'dags'),include_examples=False)
assert not bag.import_errors,bag.import_errors
dag=bag.dags['agri_prices_etl'];check_cycle(dag)

def configure(variant):
 for part in parts:
  def adapter(p=part):
   if variant=='dit_outage' and p['source']=='dit':
    raise ConnectionError('TEST ONLY: injected DIT outage; no source request made')
   if not p['ok']:raise RuntimeError(p['error'])
   rows=copy.deepcopy(p['rows'])
   if variant=='invalid_price' and p['source']=='dit':rows[0]['price_min']='-1'
   return rows
  setattr(collectors,'collect_'+part['source'],adapter)

def count():
 with psycopg2.connect(DSN) as c:
  with c.cursor() as q:q.execute('SELECT count(*) FROM agricultural_prices');return q.fetchone()[0]

def run(label,minute,variant='baseline'):
 configure(variant)
 result=dag.test(execution_date=BASE_TIME.add(seconds=minute),
  run_conf={'input_mode':'verified_snapshot_replay','scenario':label})
 return {'scenario':label,'state':str(result.state),'count':count()}

with psycopg2.connect(DSN) as c:
 with c.cursor() as q:
  q.execute(open(ROOT/'sql/001_init.sql').read())
  q.execute('SELECT version()');version=q.fetchone()[0]
  q.execute('SELECT count(*) FROM agricultural_prices');assert q.fetchone()[0]==0,'Use an empty isolated DB'
c.close()
results=[run('baseline',31),run('repeat_upsert',32),run('dit_outage',33,'dit_outage')]
assert all(r['state']=='success' and r['count']==len(expected) for r in results)
results.append(run('invalid_price_branch',34,'invalid_price'))
assert results[-1]['state']=='failed' and results[-1]['count']==len(expected)
fields=('observation_key','source','source_record_id','product_name','product_code','province','market_name','unit','price_min','price_max','observed_at','measurement_type','source_url')
with psycopg2.connect(DSN) as c:
 with c.cursor() as q:
  q.execute('SELECT '+','.join(fields)+' FROM agricultural_prices ORDER BY observation_key')
  actual=[dict(zip(fields,r)) for r in q.fetchall()]
  for a,e in zip(actual,sorted(expected,key=lambda x:x['observation_key'])):
   for field in fields:
    if field.startswith('price_'):assert Decimal(a[field])==Decimal(e[field]),field
    elif field=='observed_at':assert str(a[field])==e[field]
    else:assert a[field]==e.get(field),(field,a[field],e.get(field))
  constraint_results={}
  for name,sql,code in [
   ('nonnegative','UPDATE agricultural_prices SET price_min=-1 WHERE id=(SELECT min(id) FROM agricultural_prices)','23514'),
   ('range_order','UPDATE agricultural_prices SET price_max=price_min-1 WHERE id=(SELECT min(id) FROM agricultural_prices)','23514'),
   ('unique','INSERT INTO agricultural_prices ('+','.join(fields)+') SELECT '+','.join(fields)+' FROM agricultural_prices LIMIT 1','23505')]:
   q.execute('SAVEPOINT invalid_probe')
   try:q.execute(sql)
   except psycopg2.Error as e:
    assert e.pgcode==code,(name,e.pgcode)
    constraint_results[name]={'passed':True,'sqlstate':e.pgcode}
   else:raise AssertionError('Constraint did not reject '+name)
   finally:q.execute('ROLLBACK TO SAVEPOINT invalid_probe')
  q.execute('SELECT source,count(*) FROM agricultural_prices GROUP BY source ORDER BY source');sources=dict(q.fetchall())
  q.execute('SELECT run_id,status,loaded_rows,details FROM pipeline_runs ORDER BY run_id');audit=q.fetchall()
 c.rollback()
summary={'engine':version,'metadata':'SQLite for local dag.test only','input':'Original captured source rows from evidence/collection-three-sources.json; network extraction not repeated in these integration runs',
 'scenarios':results,'expected_rows':len(expected),'persisted_rows':count(),'all_13_fields_match_snapshot':True,'sources':sources,'constraints':constraint_results,'pipeline_runs':audit,
 'native_postgres16_docker_validated':False}
(ROOT/'evidence/integration-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=str))
print('INTEGRATION SUMMARY',json.dumps(summary,ensure_ascii=False,default=str))
