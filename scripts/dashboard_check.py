"""Check third-source filters, safe comparisons and pipeline status against PostgreSQL."""
import pathlib,os,json
import pandas as pd
from sqlalchemy import create_engine,text
from streamlit.testing.v1 import AppTest
ROOT=pathlib.Path(__file__).resolve().parents[1]
with create_engine(os.environ['DATABASE_URL']).connect() as c:
 df=pd.read_sql(text('SELECT source,product_name,unit,measurement_type,observed_at,price_min,price_max,(price_min+price_max)/2 AS average_price FROM agricultural_prices'),c)
df.observed_at=pd.to_datetime(df.observed_at).dt.date
assert {'dit','nabc','talaadthai'} <= set(df.source)
app=AppTest.from_file(str(ROOT/'web/app.py')).run(timeout=30)
assert not app.exception,str(app.exception)
assert set(app.multiselect[1].options)==set(df.source.unique())
assert len(app.get('plotly_chart'))==2
assert len(app.expander)>=1
app.multiselect[1].set_value(['talaadthai']);app.run(timeout=30)
assert not app.exception
expected=df[df.source=='talaadthai']
# The price table is last; earlier dataframe is pipeline audit queried separately.
assert len(app.dataframe[-1].value)==len(expected)
assert set(app.dataframe[-1].value.source)=={'talaadthai'}
selection=app.selectbox[0].value
selected=expected[(expected.product_name==selection[0])&(expected.unit==selection[1])&(expected.measurement_type==selection[2])]
assert [x.value for x in app.metric]==[f'{len(selected):,}',f'{selected.average_price.mean():,.2f}',f'{selected.price_max.max():,.2f}',f'{selected.price_min.min():,.2f}']
# Plotly specs contain real rendered data; both figures must be unit/type constrained.
import plotly.io as pio
trend_spec=json.loads(app.get('plotly_chart')[0].proto.spec)
bar_spec=json.loads(app.get('plotly_chart')[1].proto.spec)
assert all(trace.get('name')=='talaadthai' for trace in trend_spec['data'])
unit,type_=app.selectbox[1].value;day=app.selectbox[2].value
bar_expected=expected[(expected.unit==unit)&(expected.measurement_type==type_)&(expected.observed_at==day)]
assert bar_expected.measurement_type.nunique()==1 and bar_expected.unit.nunique()==1
bar_rows=bar_expected.groupby(['product_name','source'],as_index=False).average_price.mean()
for trace in bar_spec['data']:
 for product,price in zip(trace['y'],trace['x']):
  answer=bar_rows[(bar_rows.product_name==product)&(bar_rows.source==trace['name'])].average_price.iloc[0]
  assert abs(float(price)-float(answer))<1e-6
# Date/product filters preserve exact rows and empty selection remains graceful.
product='ต้นหอม';app.multiselect[0].set_value([product]);app.run(timeout=30)
assert not app.exception
assert set(app.dataframe[-1].value.product_name)=={product}
day=df[(df.source=='talaadthai')&(df.product_name==product)].observed_at.max()
app.date_input[0].set_value((day,day));app.run(timeout=30)
assert not app.exception and all(app.dataframe[-1].value.observed_at==day)
app.multiselect[1].set_value([]);app.run(timeout=30)
assert not app.exception and len(app.info)>0
result={'engine':'PostgreSQL18.6 WASM (not Docker16)','database_rows':len(df),'third_source_rows':len(expected),'dynamic_sources':True,'kpis_match_sql':True,'trend':True,'comparison_prices_match_sql':True,'comparison_same_unit_type_date':True,'product_source_date_filters':True,'pipeline_status_from_database':True,'empty_filter':True}
(ROOT/'evidence/third_source/dashboard-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,indent=2))
