import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly as py
import pandas as pd
import sys
import os
import pandas as pd
from os import walk
import glob
import fnmatch
import numpy as np

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
    # fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    py.offline.plot(fig)

@task
@load_plugin_env_vars("FabCovid19")
def facs_locationmap(output_dir, location_types='all', plot_replications=False, houses=False):
    results_dir = locate_results_dir(output_dir)
    borough = extract_location_name(results_dir)
    location_types = location_types.split(';')

    flag = False

    for root, dirs, files in os.walk(results_dir, topdown=True):
        for name in files:
            if "_buildings.csv" in name and borough in root:
                filepath = os.path.join(root, name)
                print("file found at:", filepath)
                df = pd.read_csv(filepath, names=['type', 'lon', 'lat', 'area'])
                title = 'Map of {}'.format(borough.title())
                plot(df, location_types, houses, title)
                flag = True
            if flag and not plot_replications:
                break