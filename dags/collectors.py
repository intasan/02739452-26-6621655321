"""Real source adapters. No synthetic fallback."""
import os
import requests
from bs4 import BeautifulSoup

TIMEOUT=20
UA={"User-Agent":"AcademicETL/0.1 (research; respect robots.txt)"}

def get_json(url, params=None):
    r=requests.get(url, params=params, timeout=TIMEOUT, headers=UA)
    r.raise_for_status()
    return r.json()

def parse_talaadthai(html, *, today=None, lookback_days=60):
    """Parse public HTML only, not the robots-disallowed JSON/JS endpoints.

    Only accept a price range when the dated snapshot and displayed range
    agree. Never assign the scrape date to an undated or stale price.
    """
    import json
    from datetime import date
    from decimal import Decimal, InvalidOperation
    today=today or date.today()
    script=BeautifulSoup(html,"html.parser").select_one('script#__NEXT_DATA__')
    if not script: raise ValueError("Talaadthai HTML missing __NEXT_DATA__")
    try:
        products=json.loads(script.string or script.get_text())["props"]["pageProps"]["productsPriceTrending"]["data"]
    except (ValueError,KeyError,TypeError) as exc:
        raise ValueError("Talaadthai productsPriceTrending schema changed") from exc
    if not isinstance(products,list): raise ValueError("Talaadthai expected product array")
    rows=[];excluded=[]
    units={'กิโลกรัม':'บาท/กก.','กระสอบ':'บาท/กระสอบ','ถุง':'บาท/ถุง',
           'ต่อชิ้น/ตัว/หัว/ลูก':'บาท/ชิ้น/ตัว/หัว/ลูก','หวี':'บาท/หวี'}
    for p in products:
        try:
            current=p['pricingData']['latestPriceDiffProductSnapShot']['data']['current']
            day=date.fromisoformat(current['date'][:10])
            lo,hi=Decimal(str(current['minPrice'])),Decimal(str(current['maxPrice']))
            if not lo.is_finite() or not hi.is_finite() or lo<0 or hi<lo:raise ValueError('invalid price')
            if (lo,hi)!=(Decimal(str(p['priceMinThb'])),Decimal(str(p['priceMaxThb']))):
                raise ValueError('dated snapshot and displayed range disagree')
            if not 0 <= (today-day).days <= lookback_days:raise ValueError('outside verified lookback')
            name=p['title']['th'].strip();unit=units[p['unit']]
            if not name or not p['id'] or not p['slug']:raise ValueError('missing identity')
            rows.append(dict(source='talaadthai',source_record_id=f"{p['id']}:{day.isoformat()}",
                product_name=name,product_code=str(p['id']),province='ปทุมธานี',market_name='ตลาดไท',
                origin_agency='talaadthai',unit=unit,price_min=str(lo),price_max=str(hi),
                observed_at=day.isoformat(),measurement_type='wholesale',
                source_url='https://talaadthai.com/products/'+p['slug']))
        except (KeyError,ValueError,TypeError,InvalidOperation,AttributeError) as exc:
            excluded.append({'product_id':str(p.get('id','')),'reason':str(exc)})
    if not rows:raise ValueError('Talaadthai has no unambiguous recent price observations')
    return rows,{'page_records':len(products),'accepted':len(rows),'excluded':excluded}

def collect_talaadthai():
    """Two polite HTTP requests: robots.txt and public products HTML."""
    from urllib.robotparser import RobotFileParser
    url='https://talaadthai.com/products'
    robot_url='https://talaadthai.com/robots.txt'
    response=requests.get(robot_url,headers=UA,timeout=TIMEOUT)
    if response.status_code==200:
        parser=RobotFileParser();parser.parse(response.text.splitlines())
        if not parser.can_fetch(UA['User-Agent'],url):raise PermissionError('Talaadthai robots.txt disallows /products')
    elif response.status_code not in (404,410):
        raise PermissionError(f'Cannot verify Talaadthai robots.txt: {response.status_code}')
    page=requests.get(url,headers=UA,timeout=TIMEOUT);page.raise_for_status()
    rows,report=parse_talaadthai(page.text,lookback_days=int(os.getenv('TALAADTHAI_LOOKBACK_DAYS','60')))
    import logging
    logging.getLogger(__name__).info('Talaadthai extraction quality: %s',report)
    return rows

def parse_dit(html, code):
    import re
    from datetime import date
    soup=BeautifulSoup(html,"html.parser")
    option=soup.select_one(f'#proname option[value="{code}"]')
    if not option: raise ValueError("Selected DIT product missing")
    name=option.get_text(" ",strip=True)
    units=[x.get_text(" ",strip=True) for x in soup.select("span") if "บาท/" in x.get_text()]
    if len(units)!=1: raise ValueError("Cannot determine unique DIT unit")
    unit=re.search(r"บาท/[^\s<]+",units[0]).group()
    months=['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.']
    table=soup.select_one('table.table-striped')
    if not table or 'วันที่' not in table.get_text(): raise ValueError("DIT table schema changed")
    rows=[]
    for tr in table.select('tbody tr'):
        cells=[c.get_text(" ",strip=True) for c in tr.select('td')]
        if not cells or cells[0]=='ราคาเฉลี่ย': continue
        if len(cells)!=3: raise ValueError("DIT row schema changed")
        d,m,y=cells[0].split()
        day=date(int(y)-543,months.index(m)+1,int(d)).isoformat()
        match=re.fullmatch(r'([\d,.]+)\s*-\s*([\d,.]+)',cells[1])
        if not match: raise ValueError("DIT price schema changed")
        lo,hi=[v.replace(',','') for v in match.groups()]
        rows.append(dict(source='dit',source_record_id=f'{code}:retail:{day}',product_code=code,
            product_name=name,province='กรุงเทพมหานคร',market_name=None,origin_agency='dit',unit=unit,
            price_min=lo,price_max=hi,observed_at=day,measurement_type='retail',
            source_url='https://pricelist.dit.go.th/main_price.php?seltime=day'))
    if not rows: raise ValueError("DIT returned no observations")
    return rows

def collect_dit():
    from datetime import date,timedelta
    from urllib.robotparser import RobotFileParser
    import time
    base='https://pricelist.dit.go.th/'
    robots=requests.get(base+'robots.txt',headers=UA,timeout=TIMEOUT)
    if robots.status_code==200:
        parser=RobotFileParser();parser.parse(robots.text.splitlines())
        if not parser.can_fetch(UA['User-Agent'],base+'main_price.php'):
            raise PermissionError('DIT robots.txt disallows prices')
    elif robots.status_code not in (404,410):
        raise PermissionError(f'Cannot verify robots.txt: HTTP {robots.status_code}')
    # 404/410: no robots rules published; no authentication or personal data collected.
    today=date.today();start=today-timedelta(days=int(os.getenv('LOOKBACK_DAYS','60')))
    output=[]
    for code in os.getenv('DIT_PRODUCT_CODES','P13001,P13003').split(','):
        code=code.strip()
        if not code.startswith('P13'):raise ValueError('Verified DIT scope is vegetable group P13000')
        response=requests.post(base+'main_price.php?seltime=day',headers=UA,timeout=TIMEOUT,
            data={'day1':start.strftime('%d/%m/')+str(start.year+543),
                  'day2':today.strftime('%d/%m/')+str(today.year+543),
                  'protype':'1','progroup':'P13000','proname':code,'seltime':'day'})
        response.raise_for_status();output.extend(parse_dit(response.text,code));time.sleep(0.5)
    return output

def collect_nabc():
    """Live-verified NABC date endpoint, paginated and bounded."""
    from datetime import date,timedelta
    import hashlib,json,time
    output=[]
    for offset in range(1,int(os.getenv("NABC_LOOKBACK_DAYS","7"))+1):
        day=(date.today()-timedelta(days=offset)).isoformat()
        for page in range(1,101):
            url="https://agriapi.nabc.go.th/api/daily-prices/date"
            payload=get_json(url,{"date":day,"limit":100,"page":page})
            if not isinstance(payload,dict) or payload.get("success") is not True or not isinstance(payload.get("data"),list):
                raise ValueError("Unexpected NABC response schema")
            rows=payload["data"]
            for r in rows:
                identity=[r["data_date"],r["product_name"],r["market_name"],r["province"],r["unit"]]
                output.append(dict(source="nabc",source_record_id=hashlib.sha256(json.dumps(identity,ensure_ascii=False).encode()).hexdigest(),
                    product_name=r["product_name"],product_code=None,province=r["province"],market_name=r["market_name"],
                    unit=r["unit"],price_min=r["day_price"],price_max=r["day_price"],observed_at=r["data_date"][:10],
                    measurement_type="market_buying",source_url=url+"?date="+day))
            if len(rows)<100: break
            time.sleep(0.3)
        else: raise RuntimeError("NABC pagination safety limit reached")
        time.sleep(0.3)
    return output
