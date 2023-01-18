import pandas as pd
import plotly.express as px
from pathlib import Path


from plugins.FabCovid19.FabCovid19 import *
from .facs_postprocess_utils import *

@task
@load_plugin_env_vars("FabCovid19")
def facs_mapspread(path, day, types='all'):

    ll = Path(env.local_results).rglob('*')
    ll = [str(p) for p in ll]

    base = len(env.local_results.split('/'))

    ll = [x for x in ll if len(x.split('/')) == base + 4 and 'covid_out_infections' in x.split('/')[-1] and x.split('/')[-3] == 'RUNS']
    ll = [x for x in ll if x.split('/')[-4] == path]

    lon = []
    lat = []
    typ = []

    if '-' in day:
        delta = day.split('-')
        delta = [int(x) for x in delta]
    else:
        delta = [int(day), int(day)]

    for ff in ll:

        df = pd.read_csv(ff)

        df = df[df['#time'] >= delta[0]]
        df = df[df['#time'] <= delta[1]]

        lon.extend(df['x'])
        lat.extend(df['y'])
        typ.extend(df['location_type'])

    dd = pd.DataFrame()
    dd['lon'] = lon
    dd['lat'] = lat
    dd['type'] = typ

    if types != 'all':
        dd = dd[dd['type'] == types]

    title = 'Test'
    title = 'Spread of infections'
    fig = px.scatter_mapbox(dd, lon='lon', lat='lat', color='type', zoom=10, title=title)
    # fig.update_layout(mapbox_style="carto-darkmatter")
    fig.update_layout(mapbox_style="open-street-map")

    fig.show()
