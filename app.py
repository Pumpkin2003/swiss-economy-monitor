"""Swiss Economy Monitor — Streamlit dashboard using official public APIs."""
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_pipeline import fetch_all

st.set_page_config(page_title='Swiss Economy Monitor', page_icon='🇨🇭', layout='wide')
st.markdown('''<style>
.block-container{max-width:1180px;padding-top:1.7rem}
h1,h2,h3{letter-spacing:-.025em}
[data-testid="stMetric"]{background:#f8f9fc;border:1px solid #e8eaf0;padding:14px;border-radius:12px}
small,.tiny{color:#65717f}
</style>''', unsafe_allow_html=True)

SNAPSHOT = Path(__file__).parent / 'data' / 'snapshot.json'

@st.cache_data(ttl=3600, show_spinner=False)
def live_refresh():
    return fetch_all()


def load_snapshot():
    if SNAPSHOT.exists():
        data = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
        if data.get('series'):
            return data
    return None


def load_data():
    if 'fresh_data' in st.session_state:
        return st.session_state.fresh_data, 'Live fetch in this session'
    stored = load_snapshot()
    if stored:
        return stored, 'Last successful scheduled GitHub Actions snapshot'
    try:
        return live_refresh(), 'Initial live fetch (not a scheduled refresh)'
    except Exception as exc:
        st.error(f'Official data could not be loaded: {exc}. No invented fallback values are displayed.')
        st.stop()

st.title('🇨🇭 Swiss Economy Monitor')
st.caption('A quarter century of economic performance · Official statistics · 2000 to latest available')
st.markdown('**Question:** Is Switzerland staying economically resilient, and how does the Swiss franc fit into the picture?')

with st.sidebar:
    st.header('Explore')
    period = st.selectbox('Historical window', ['Since 2000', 'Since 2005', 'Since 2015', 'Last 5 years'], index=0)
    st.caption('World Bank: annual macroeconomic series · ECB: daily FX reference rates.')
    if st.button('↻ Refresh official data now', use_container_width=True):
        try:
            live_refresh.clear()
            st.session_state.fresh_data = live_refresh()
            st.success('Live refresh succeeded. Charts now use the newly retrieved data.')
            st.rerun()
        except Exception as exc:
            st.error(f'Refresh failed: {exc}. The last successful dataset is retained.')
    if st.button('Use scheduled snapshot again', use_container_width=True):
        st.session_state.pop('fresh_data', None)
        st.rerun()

snapshot, mode = load_data()
start_year = {'Since 2000':2000, 'Since 2005':2005, 'Since 2015':2015, 'Last 5 years':datetime.now(timezone.utc).year-5}[period]
st.info(f"**Last successful data refresh (UTC):** {snapshot['last_successful_refresh_utc']}  ·  **Data mode:** {mode}.  **Latest observation dates** are shown on each chart separately. A refresh can succeed without new observations.")

series = snapshot['series']
cols = st.columns(4)
for col, k in zip(cols, ['gdp','inflation','unemployment','eur_chf']):
    item = series[k]
    last = item['observations'][-1]
    fmt = f"{last['value']:.2f}%" if k != 'eur_chf' else f"{last['value']:.4f}"
    col.metric(item['title'], fmt, help=f"Latest observation: {last['date']}; {item['source']}")

st.subheader('Economic indicators')
st.caption('Each chart uses its own stated frequency. Annual and daily observations are not interpolated.')

order = ['gdp','inflation','unemployment','current_account','exports','eur_chf','usd_chf']
for i in range(0, len(order), 2):
    left_right = st.columns(2)
    for col, k in zip(left_right, order[i:i+2]):
        item = series[k]
        data = pd.DataFrame(item['observations'])
        data['date'] = pd.to_datetime(data['date'])
        data = data.loc[data.date.dt.year >= start_year]
        with col:
            st.markdown(f"#### {item['title']}")
            chart = go.Figure()
            chart.add_trace(go.Scatter(x=data.date, y=data.value, mode='lines+markers' if 'Annual' in item['frequency'] else 'lines', name=item['title'], line=dict(color='#c73543', width=2.4), marker=dict(size=5)))
            chart.add_hline(y=0, line=dict(color='#a0a5b0', width=1, dash='dot')) if k in ('gdp','inflation','current_account') else None
            chart.update_layout(height=285, margin=dict(l=10,r=10,t=8,b=4), showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False), yaxis=dict(title=item['units'], gridcolor='#ecedf1'))
            st.plotly_chart(chart, use_container_width=True, key=k)
            st.caption(f"**Unit:** {item['units']} · **Frequency:** {item['frequency']} · **Source:** {item['source']} · **Latest observation:** {item['latest_observation']}")
            with st.expander('Definition, transformation & original source'):
                st.write(item['transformation'])
                st.write(f"Source's reported update: {item['source_release']}")
                st.markdown(f"[Open original source data]({item['url']})")

st.subheader('Verification & data provenance')
st.write('The table gives the **latest actual observed value** of every series and a direct link to its official API. Use these to compare at least one observation from each series against the original source. The independent checks should be documented with screenshots or a table in your submission.')
records = []
for k in order:
    item = series[k]
    last = item['observations'][-1]
    records.append({'Indicator':item['title'], 'Last observation':item['latest_observation'], 'Value':last['value'], 'Unit':item['units'], 'Frequency':item['frequency'], 'Original source URL':item['url']})
checks = pd.DataFrame(records)
st.dataframe(checks, hide_index=True, use_container_width=True)
st.download_button('Download latest observations (CSV)', checks.to_csv(index=False).encode('utf-8'), 'swiss_economy_verification.csv', mime='text/csv')
raw = pd.DataFrame([{'series':k, 'date':point['date'], 'value':point['value'], 'units':series[k]['units']} for k in order for point in series[k]['observations']])
st.download_button('Download full time series (CSV)', raw.to_csv(index=False).encode('utf-8'), 'swiss_economy_series.csv', mime='text/csv')

with st.expander('How the automatic refresh works'):
    st.markdown('''**Scheduled:** GitHub Actions runs daily at 08:15 UTC and executes `python data_pipeline.py`. A successful run updates `data/snapshot.json` in the repository, with a UTC timestamp and each series’ latest observation date. The Actions job log is evidence of the refresh. **Manual:** “Refresh official data now” requests the live APIs in this Streamlit session. **Failure:** an unsuccessful request never advances the last-successful timestamp or invents observations. The daily schedule is independent of the Streamlit cache. Actual run times may vary with GitHub Actions scheduling.''')
    st.markdown('**Sources:** World Bank World Development Indicators (5 series), European Central Bank euro-reference FX rates (2 series; USD/CHF derived from two matching-date ECB quotes).')
st.caption('Educational economic monitor. Official observations may be revised and released on different schedules. Historical events are context, not causal estimates.')
