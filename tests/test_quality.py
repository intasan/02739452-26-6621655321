"""Tests use observations downloaded from the real DIT response.
Fault injection mutates copies only and never creates production records.
"""
import json, pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'dags'))
from collectors import parse_dit
from quality import merge_and_validate,branch_target
RAW=json.loads((pathlib.Path(__file__).resolve().parents[1]/'evidence/dit-price.json').read_text())
REAL=parse_dit(RAW['body'],'P13001')
def part(rows,source='dit',ok=True):return {'source':source,'rows':rows,'ok':ok,'error':None if ok else 'injected outage'}
def test_real_html_parse():
 assert len(REAL)==55
 assert REAL[0]['observed_at']=='2026-08-03'
 assert REAL[0]['price_min']=='30'
def test_duplicate_and_id_stability():
 a=merge_and_validate([part(REAL)]);b=merge_and_validate([part(REAL+REAL)])
 assert a['rows']==b['rows'] and b['duplicates']==55
 assert len(set(r['observation_key'] for r in a['rows']))==55
def test_cross_source_duplicate():
 alias=dict(REAL[0],source='moc')
 r=merge_and_validate([part(REAL[:1]),part([alias],'moc')])
 assert len(r['rows'])==1 and r['duplicates']==1
def test_outage_isolation():
 r=merge_and_validate([part(REAL),part([],'moc',False)])
 assert branch_target(r)=='load_prices' and len(r['errors'])==1
def test_reject_nonfinite_and_negative():
 for price in ['NaN','Infinity','-1']:
  r=merge_and_validate([part([dict(REAL[0],price_min=price)])])
  assert r['rejected']==1 and branch_target(r)=='no_valid_data'
def test_empty_branch():
 assert branch_target(merge_and_validate([part([],'dit',False)]))=='no_valid_data'
def test_revision_has_same_upsert_key():
 a=merge_and_validate([part(REAL[:1])]);b=merge_and_validate([part([dict(REAL[0],price_max='40')])])
 assert a['rows'][0]['observation_key']==b['rows'][0]['observation_key']

def test_same_numeric_price_different_format_is_duplicate():
 alias=dict(REAL[0],source='moc',price_min='30.00',price_max='35.0')
 r=merge_and_validate([part(REAL[:1]),part([alias],'moc')])
 assert r['rejected']==0 and r['duplicates']==1

def test_same_name_different_market_is_not_duplicate():
 other=dict(REAL[0],market_name='different_market_for_fault_isolation_test')
 r=merge_and_validate([part([REAL[0],other])])
 assert len(r['rows'])==2

def test_conflicting_price_rejected():
 other=dict(REAL[0],source='moc',price_min='31')
 r=merge_and_validate([part(REAL[:1]),part([other],'moc')])
 assert r['rejected']==1 and branch_target(r)=='no_valid_data'
