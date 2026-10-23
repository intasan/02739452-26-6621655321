"""Export queried real prices and counts for inspection; never exports credentials."""
import pathlib,os,json
from contextlib import closing
import psycopg2
ROOT=pathlib.Path(__file__).resolve().parents[1]
with closing(psycopg2.connect(os.environ['APP_DATABASE_URL'])) as c,c:
 with c.cursor() as q:
  q.execute('SELECT version()');version=q.fetchone()[0]
  q.execute('SELECT observation_key,source,source_record_id,product_name,product_code,province,market_name,unit,price_min,price_max,observed_at,measurement_type,source_url FROM agricultural_prices ORDER BY observation_key')
  fields=[d.name for d in q.description];rows=[dict(zip(fields,r)) for r in q.fetchall()]
(ROOT/'evidence/database-export.json').write_text(json.dumps({'engine':version,'count':len(rows),'rows':rows},ensure_ascii=False,indent=2,default=str))
print('Exported actual database rows:',len(rows))
