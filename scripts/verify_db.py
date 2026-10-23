"""Run after a real DAG run; never inserts sample data."""
import os
from contextlib import closing
import psycopg2
from psycopg2.extras import execute_values
FIELDS='observation_key,source,source_record_id,product_name,product_code,province,market_name,unit,price_min,price_max,observed_at,measurement_type,source_url'
with closing(psycopg2.connect(os.environ['APP_DATABASE_URL'])) as conn:
 with conn.cursor() as cur:
  cur.execute('SELECT count(*) FROM agricultural_prices');before=cur.fetchone()[0]
  if before<100:raise RuntimeError(f'Only {before} real records; requirement >=100 not met')
  cur.execute(f'SELECT {FIELDS} FROM agricultural_prices');rows=cur.fetchall()
  execute_values(cur,f'INSERT INTO agricultural_prices ({FIELDS}) VALUES %s ON CONFLICT (observation_key) DO UPDATE SET price_min=EXCLUDED.price_min,price_max=EXCLUDED.price_max',rows)
  cur.execute('SELECT count(*) FROM agricultural_prices');after=cur.fetchone()[0]
  assert before==after,(before,after)
  cur.execute('SELECT source,count(*) FROM agricultural_prices GROUP BY source');print({'before':before,'after':after,'sources':cur.fetchall()})
 conn.rollback() # verification is non-destructive
