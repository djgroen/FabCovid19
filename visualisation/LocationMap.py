import plotly.express as px
import plotly as py
import pandas as pd
import pandas as pd

from plugins.FabCovid19.FabCovid19 import *
from .facs_postprocess_utils import *

def plot(df, types, houses, title):

    if types != ['all']:
        dd = pd.DataFrame()
        for t in types:
            dd = dd.append(df[df['type'] == t])
        df = dd
    elif houses == False:
        df = df[df['type'] != 'house']
 
    fig = px.scatter_mapbox(df,lon='lon', lat='lat', color='type', zoom=10, title=title)
    fig.update_layout(mapbox_style="open-street-map")

    py.offline.plot(fig)

@task
@load_plugin_env_vars("FabCovid19")
def facs_locationmap(region, location_types='all', plot_replications=False, houses=False):

    fname = '{}/config_files/{}/covid_data/{}_buildings.csv'.format(env.localplugins["FabCovid19"], region, region)
    print(fname)
    df = pd.read_csv(fname, names=['type', 'lon', 'lat', 'area'])
    location_types = location_types.split(';')
    title = 'Map of {}'.format(region.title())
    plot(df, location_types, houses, title)