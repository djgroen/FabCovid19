import plotly.graph_objects as go
import plotly as py
import pandas as pd
import sys
import os
import pathlib
import plotly.express as px
from datetime import datetime
from datetime import timedelta
from plotly.subplots import make_subplots
from pprint import pprint
from pathlib import Path


from plugins.FabCovid19.FabCovid19 import *
from .facs_postprocess_utils import *

def filter_files(filename, region, machine, cores, measures):

    ll = Path(env.local_results).rglob('*')
    ll = [str(p) for p in ll]

    base = len(env.local_results.split('/'))

    ll = [x for x in ll if len(x.split('/')) == base + 4 and filename in x.split('/')[-1] and x.split('/')[-3] == 'RUNS']
    ll = [x for x in ll if '_'.join(x.split('/')[-4].split('_')[:-2]) in region]
    ll = [x for x in ll if x.split('/')[-4].split('_')[-2] in machine]
    ll = [x for x in ll if x.split('/')[-4].split('_')[-1] in cores]
    ll = [x for x in ll if '_'.join(x.split('/')[-2].split('_')[:-1]) in measures]

    return ll

def day_to_index(region, machine, cores, measures, day):

    if '-' in day:
        a = day.split('-')
    else:
        a = [day, day]

    ll = filter_files('out.csv', region, machine, cores, measures)

    df = pd.read_csv(ll[0])

    s = datetime.strptime(df.iloc[0,1], '%d/%m/%Y').date()

    sa = datetime.strptime(a[0], '%d/%m/%Y').date()
    sb = datetime.strptime(a[1], '%d/%m/%Y').date()

    return [(sa-s).days, (sb-s).days]

@task
@load_plugin_env_vars("FabCovid19")
def facs_mapspread(region, machine, cores, measures, day):

    ll = filter_files('covid_out_infections', region, machine, cores, measures)

    lon = []
    lat = []
    typ = []

    delta = day_to_index(region, machine, cores, measures, day)

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
    dd['typ'] = typ

    title = 'Spread of infections in {} from {} to {} with measures defined in {} file'.format(region.title(), day.split('-')[0], day.split('-')[1], measures)
    fig = px.scatter_mapbox(dd, lon='lon', lat='lat', color='typ', zoom=10, title=title)
    fig.update_layout(mapbox_style="open-street-map")

    py.offline.plot(fig)
