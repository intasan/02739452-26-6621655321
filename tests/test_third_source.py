"""Fixtures are the unmodified real public HTML response, not sample prices."""
import sys,json,pathlib
from datetime import date
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'dags'))
from collectors import parse_talaadthai
from quality import merge_and_validate
RAW=json.loads((ROOT/'evidence/third_source/talaadthai-products.json').read_text())
def test_verified_html_source():
 rows,audit=parse_talaadthai(RAW['body'],today=date(2026,10,23))
 assert len(rows)==44 and audit['page_records']==67 and len(audit['excluded'])==23
 assert {r['source'] for r in rows}=={'talaadthai'}
 assert rows[0]['product_name']=='มะนาวเบอร์ 400 /กระสอบ'
 assert rows[0]['price_min']=='1050' and rows[0]['price_max']=='1200'
 assert rows[0]['observed_at']=='2026-10-23' and rows[0]['unit']=='บาท/กระสอบ'
 assert all(r['measurement_type']=='wholesale' for r in rows)
def test_existing_keys_preserved_and_new_source_isolated():
 old=json.loads((ROOT/'evidence/collection.json').read_text())
 baseline=[p for p in old['sources'] if p['source'] in ('dit','nabc')]
 before=merge_and_validate(baseline)
 rows,_=parse_talaadthai(RAW['body'],today=date(2026,10,23))
 after=merge_and_validate(baseline+[dict(source='talaadthai',ok=True,rows=rows,error=None)])
 assert len(before['rows'])==354 and len(after['rows'])==398 and after['rejected']==0
 assert {r['observation_key'] for r in before['rows']} <= {r['observation_key'] for r in after['rows']}
 outage=merge_and_validate(baseline+[dict(source='talaadthai',ok=False,rows=[],error='TEST: simulated connection failure')])
 assert len(outage['rows'])==354 and len(outage['errors'])==1
