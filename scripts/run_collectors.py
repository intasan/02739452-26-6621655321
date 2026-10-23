import concurrent.futures,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'dags'))
from collectors import collect_dit,collect_talaadthai,collect_nabc
from quality import merge_and_validate

def fetch(pair):
 source,fn=pair
 try:return dict(source=source,ok=True,rows=fn(),error=None)
 except Exception as e:return dict(source=source,ok=False,rows=[],error=f'{type(e).__name__}: {e}')
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  parts=list(pool.map(fetch,[('dit',collect_dit),('talaadthai',collect_talaadthai),('nabc',collect_nabc)]))
 result=merge_and_validate(parts)
 path=pathlib.Path(__file__).resolve().parents[1]/'evidence'/'collection-three-sources.json'
 path.write_text(json.dumps({'sources':parts,'validation':result},ensure_ascii=False,indent=2))
 print(json.dumps({'sources':[{k:v for k,v in p.items() if k!='rows'}|{'rows':len(p['rows'])} for p in parts], 'valid_rows':len(result['rows']),'rejected':result['rejected']},ensure_ascii=False,indent=2))
