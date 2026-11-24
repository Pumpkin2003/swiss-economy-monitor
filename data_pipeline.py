"""Fetch and validate official World Bank and ECB series for Switzerland."""
from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from pathlib import Path
import requests
import pandas as pd

WB_SERIES = {
    'gdp': ('NY.GDP.MKTP.KD.ZG', 'Real GDP growth', '% year over year', 'Annual', 'Annual growth of constant-price GDP; World Development Indicators.'),
    'inflation': ('FP.CPI.TOTL.ZG', 'Consumer price inflation', '% year over year', 'Annual', 'Annual rate based on the consumer price index; WDI.'),
    'unemployment': ('SL.UEM.TOTL.ZS', 'Unemployment rate (ILO estimate)', '% of labor force', 'Annual', 'ILO-modeled unemployment, not the Swiss registered unemployment rate.'),
    'current_account': ('BN.CAB.XOKA.GD.ZS', 'Current account balance', '% of GDP', 'Annual', 'Current account balance scaled by current-price GDP.'),
    'exports': ('NE.EXP.GNFS.ZS', 'Exports of goods and services', '% of GDP', 'Annual', 'Exports relative to GDP; includes goods and services.'),
}
ECB_URL = 'https://data-api.ecb.europa.eu/service/data/EXR/D.CHF+USD.EUR.SP00.A?format=csvdata&startPeriod=2000-01-01'
HEADERS = {'User-Agent': 'SwissEconomyMonitor/1.0 (education; public official statistical data)', 'Accept': 'text/csv, application/json'}


def get_response(url, session=requests, timeout=45):
    response = session.get(url, timeout=timeout, headers=HEADERS)
    response.raise_for_status()
    return response


def fetch_wb(code, session=requests):
    url = f'https://api.worldbank.org/v2/country/CHE/indicator/{code}?format=json&date=2000:{datetime.now(timezone.utc).year}&per_page=200'
    payload = get_response(url, session).json()
    if not isinstance(payload, list) or len(payload) != 2 or not isinstance(payload[1], list):
        raise ValueError(f'World Bank malformed response for {code}')
    meta, rows = payload
    observations = sorted([{'date': str(x['date']), 'value': float(x['value'])} for x in rows if x.get('value') is not None], key=lambda x: x['date'])
    if len(observations) < 8:
        raise ValueError(f'Insufficient World Bank observations for {code}')
    return observations, url, meta.get('lastupdated', 'Not supplied')


def parse_ecb_csv(text):
    df = pd.read_csv(io.StringIO(text), low_memory=False)
    expected = {'CURRENCY', 'TIME_PERIOD', 'OBS_VALUE'}
    if not expected.issubset(df.columns):
        raise ValueError('ECB response missing required columns')
    df = df.loc[df['CURRENCY'].isin(['CHF', 'USD']), ['CURRENCY', 'TIME_PERIOD', 'OBS_VALUE']].copy()
    df['OBS_VALUE'] = pd.to_numeric(df['OBS_VALUE'], errors='coerce')
    df['TIME_PERIOD'] = pd.to_datetime(df['TIME_PERIOD'], errors='coerce')
    df = df.dropna().drop_duplicates(['CURRENCY', 'TIME_PERIOD'], keep='last')
    rates = df.pivot(index='TIME_PERIOD', columns='CURRENCY', values='OBS_VALUE').sort_index()
    if not {'CHF', 'USD'}.issubset(rates.columns):
        raise ValueError('ECB CHF and USD euro-reference series are required')
    if not ((rates['CHF'] > 0).all() and (rates['USD'] > 0).all()):
        raise ValueError('Nonpositive FX rate')
    eur_chf = rates['CHF'].dropna()
    usd_chf = (rates['CHF'] / rates['USD']).dropna()
    if len(eur_chf) < 1000 or len(usd_chf) < 1000:
        raise ValueError('Insufficient ECB daily FX observations')
    def serialize(s):
        return [{'date': i.strftime('%Y-%m-%d'), 'value': round(float(v), 7)} for i, v in s.items()]
    return serialize(eur_chf), serialize(usd_chf)


def fetch_all(session=requests, now=None):
    timestamp = (now or datetime.now(timezone.utc)).isoformat(timespec='seconds')
    series = {}
    for key, (code, title, units, frequency, note) in WB_SERIES.items():
        observations, url, release = fetch_wb(code, session)
        series[key] = dict(title=title, units=units, frequency=frequency, source='World Bank · World Development Indicators', url=url, source_release=release, transformation=note, observations=observations, latest_observation=observations[-1]['date'])
    eur, usd = parse_ecb_csv(get_response(ECB_URL, session).text)
    series['eur_chf'] = dict(title='EUR/CHF exchange rate', units='CHF per EUR', frequency='Daily (business days)', source='European Central Bank · Euro foreign exchange reference rates', url=ECB_URL, source_release='Not supplied in CSV', transformation='Original ECB CHF per EUR reference quote; a falling value means CHF appreciation against EUR.', observations=eur, latest_observation=eur[-1]['date'])
    series['usd_chf'] = dict(title='USD/CHF exchange rate', units='CHF per USD', frequency='Daily (business days)', source='European Central Bank · Euro foreign exchange reference rates', url=ECB_URL, source_release='Not supplied in CSV', transformation='Derived as (CHF per EUR) / (USD per EUR) on matching dates; a falling value means CHF appreciation against USD.', observations=usd, latest_observation=usd[-1]['date'])
    return {'country': 'Switzerland', 'last_successful_refresh_utc': timestamp, 'series': series, 'pipeline_version': 1}


def save_snapshot(snapshot, path='data/snapshot.json'):
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    snapshot = fetch_all()
    save_snapshot(snapshot)
    print(f"SUCCESSFUL REFRESH UTC: {snapshot['last_successful_refresh_utc']}")
    for key, item in snapshot['series'].items():
        print(f"CHECK {key}: last observation {item['latest_observation']}, {len(item['observations'])} points; value {item['observations'][-1]['value']}")

if __name__ == '__main__':
    main()
