"""Validation and conservative cross-source duplicate detection."""
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
import unicodedata

def normalized(value):
    return ' '.join(unicodedata.normalize('NFKC', str(value)).split()).casefold()

def merge_and_validate(parts):
    accepted, rejected, errors = {}, [], []
    # Retain different market/grade/unit observations. Equal names alone never prove duplication.
    for part in sorted(parts, key=lambda p: {'dit':0,'talaadthai':1,'nabc':2}.get(p['source'],9)):
        if not part['ok']:
            errors.append({'source':part['source'],'error':part['error']})
        for original in part['rows']:
            try:
                r = dict(original)
                for field in ('source','source_record_id','product_name','unit','source_url','measurement_type'):
                    if not r.get(field) or r[field] == 'unspecified':
                        raise ValueError('Missing comparable field: '+field)
                lo, hi = Decimal(str(r['price_min'])), Decimal(str(r['price_max']))
                if not lo.is_finite() or not hi.is_finite() or lo < 0 or hi < lo:
                    raise ValueError('Invalid price range')
                day = date.fromisoformat(str(r['observed_at'])[:10])
                if day > date.today(): raise ValueError('Future observation')
                # Explicit producer, market, grade, unit and measurement type; no fuzzy name matching.
                origin = r.get('origin_agency',r['source'])
                identity = [origin,normalized(r['product_name']),normalized(r['unit']),
                    normalized(r.get('province') or ''),normalized(r.get('market_name') or ''),
                    normalized(r['measurement_type']),day.isoformat()]
                key = hashlib.sha256(json.dumps(identity,ensure_ascii=False).encode()).hexdigest()
                r.update(price_min=str(lo),price_max=str(hi),observed_at=day.isoformat(),observation_key=key)
                if key in accepted and (Decimal(accepted[key]['price_min']),Decimal(accepted[key]['price_max'])) != (lo,hi):
                    raise ValueError('Conflicting prices for the same origin/observation')
                accepted.setdefault(key,r)
            except (ValueError,KeyError,TypeError,InvalidOperation) as e:
                rejected.append({'reason':str(e),'source':part['source']})
    rows=list(accepted.values())
    total=sum(len(p['rows']) for p in parts)
    return {'rows':rows,'rejected':len(rejected),'rejection_details':rejected,'errors':errors,
            'duplicates':total-len(rejected)-len(rows)}

def branch_target(result):
    return 'load_prices' if result['rows'] and not result['rejected'] else 'no_valid_data'
