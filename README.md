# 🇨🇭 Swiss Economy Monitor

An independently refreshable Streamlit dashboard to explore **Swiss economic resilience and the franc**, 2000–latest available.

## Dashboard question

*Is Switzerland's economy staying economically resilient, and how does the Swiss franc fit into the picture?*

Seven indicators, all from primary international organizations:

| Indicator | Definition / units | Frequency | Source |
|---|---|---|---|
| Real GDP growth | Annual growth of real GDP (%) | Annual | World Bank WDI `NY.GDP.MKTP.KD.ZG` |
| Consumer price inflation | CPI annual growth (%) | Annual | World Bank WDI `FP.CPI.TOTL.ZG` |
| Unemployment | ILO-modeled unemployment (% of labor force) | Annual | World Bank WDI `SL.UEM.TOTL.ZS` |
| Current account | Balance (% of GDP) | Annual | World Bank WDI `BN.CAB.XOKA.GD.ZS` |
| Exports | Exports of goods & services (% of GDP) | Annual | World Bank WDI `NE.EXP.GNFS.ZS` |
| EUR/CHF | Swiss francs per euro | Daily business days | ECB `EXR/D.CHF.EUR.SP00.A` |
| USD/CHF | Swiss francs per US dollar | Daily business days | Derived from ECB `CHF/EUR ÷ USD/EUR` on matching dates |

**FX direction:** lower CHF per EUR / USD = Swiss franc *appreciation*. The World Bank indicators are annual; they must not be interpreted as monthly releases. No interpolation, artificial rebasing or data imputation is done. The last observation date is distinct from the latest successful API retrieval timestamp. The latest observation may be older than the fetch time, and annual WDI data may lag or be revised.

## Deployment

1. Upload **all files including `.github/workflows/refresh-data.yml`** to the root of a public GitHub repository. GitHub's web interface may hide `.github` folders; ensure the workflow path exists.
2. Deploy via Streamlit Community Cloud with `app.py` as the main file and `main` as branch.
3. Go to GitHub repository → **Actions** → **Refresh Swiss Economic Data** → **Run workflow**. The job runs `pytest`, fetches every official API, commits the successful `data/snapshot.json`, and prints `SUCCESSFUL REFRESH UTC` and 7 `CHECK` records. Keep a screenshot of the successful job log.
4. GitHub Actions also schedules a daily refresh at **08:15 UTC**. Scheduled jobs may run late. Keep GitHub Actions enabled.
5. In Streamlit use **Refresh official data now** to re-fetch within the current session. The scheduled snapshot and session refresh are independently labelled.

**Important:** No sample numeric observations are bundled. The very first load requires a successful online API request or a successful GitHub Actions job. If an API becomes temporarily unreachable, the last successful GitHub snapshot remains available; a failed scheduled run will not commit partial data.

## Verification instructions

- Run `python -m pytest -q` (unit tests for source parsing, quote conversion and null handling).
- Download **latest observations (CSV)** from the app. Each row has original source URL, observed value, units and latest date.
- Open each original official source from the `Verification & data provenance` table and locate at least one same-year / same-date observation. For USD/CHF independently divide matching-date ECB CHF per EUR by USD per EUR. Enter checked original data, observed values, and any rounding in the submission note.
- In GitHub Actions, capture the successful run showing `SUCCESSFUL REFRESH UTC` and seven `CHECK ... last observation` entries. A successful refresh need not change values if releases have not changed.
- Include prompt, app screenshots/link, comparison table, and successful Actions log in submission.

## Technical notes

Python requests with timeouts; validation rejects malformed or very short series. The ECB API is accessed through the official SDMX CSV endpoint. World Bank WDI uses official JSON API. Failures cannot silently be turned into fake recent data. Refresh timestamp represents a completed successful run, **not** the observation date. Queries intentionally cover 2000 onward (or the series' first available observation); the date dropdown changes the plotted window only.

### Run locally

```bash
pip install -r requirements.txt
python -m pytest -q
python data_pipeline.py
streamlit run app.py
```

### API reference

- World Bank API: https://api.worldbank.org/v2/country/CHE/indicator/NY.GDP.MKTP.KD.ZG?format=json&date=2000:2026&per_page=200
- ECB exchange-rate API: https://data-api.ecb.europa.eu/service/data/EXR/D.CHF+USD.EUR.SP00.A?format=csvdata&startPeriod=2000-01-01
- ECB API guide: https://data.ecb.europa.eu/help/api/data-examples
