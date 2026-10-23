"""Read-only row count and source totals; no credentials in output."""
import argparse,os,json
from contextlib import closing
import psycopg2
parser=argparse.ArgumentParser();parser.add_argument('--count-only',action='store_true');args=parser.parse_args()
with closing(psycopg2.connect(os.environ['APP_DATABASE_URL'])) as c,c:
 with c.cursor() as q:
  q.execute('SELECT count(*) FROM agricultural_prices');count=q.fetchone()[0]
  if args.count_only:print(count)
  else:
   q.execute('SELECT source,count(*) FROM agricultural_prices GROUP BY source ORDER BY source')
   print(json.dumps({'count':count,'sources':dict(q.fetchall())}))
