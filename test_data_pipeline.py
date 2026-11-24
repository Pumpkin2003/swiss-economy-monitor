import json
from datetime import datetime, timezone
from data_pipeline import parse_ecb_csv, fetch_wb


def test_ecb_ratio_quote():
    rows = ['CURRENCY,TIME_PERIOD,OBS_VALUE']
    for i in range(1100):
        month = 1 + i // 28
        year = 2000 + (month-1)//12
        m = 1 + (month-1)%12
        day = 1 + i % 28
        rows.extend([f'CHF,{year}-{m:02d}-{day:02d},0.90', f'USD,{year}-{m:02d}-{day:02d},1.20'])
    eur, usd = parse_ecb_csv('\n'.join(rows))
    assert len(eur) == 1100
    assert len(usd) == 1100
    assert usd[-1]['value'] == 0.75
    assert eur[-1]['value'] == 0.9


def test_wb_parser_excludes_nulls_and_sorts():
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return [{'lastupdated':'2026-11-01'}, [{'date':str(year), 'value':year-2000} for year in range(2010,1999,-1)] + [{'date':'2025','value':None}]]
    class Session:
        def get(self, url, **kwargs): return Response()
    obs,url,last = fetch_wb('TEST', Session())
    assert obs[0] == {'date':'2000','value':0.0}
    assert obs[-1] == {'date':'2010','value':10.0}
    assert last == '2026-11-01'


def test_ecb_rejects_missing_currency():
    import pytest
    with pytest.raises(ValueError):
        parse_ecb_csv('CURRENCY,TIME_PERIOD,OBS_VALUE\nCHF,2026-01-01,0.9')
