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


def plot(df, output_dir, locations):
    colors = px.colors.qualitative.G10
    fig = make_subplots(rows=9, cols=1, shared_xaxes=True,
                        vertical_spacing=0.01, horizontal_spacing=0.05)
    row = 1
    for location in enumerate(locations):
        subdf = df[df['type'] == location[1]]
        fig.add_trace(go.Scatter(x=subdf['time'], y=subdf['mean'], name=location[1],  line=dict(
            color=colors[row])), row=row, col=1)
        row += 1

    fig.update_xaxes(showline=True, linewidth=1,
                     linecolor='black', mirror=True)
    fig.update_yaxes(showline=True, linewidth=1,
                     linecolor='black', mirror=True)
    fig.update_traces(mode='lines',  marker=dict(size=1, colorscale='Plotly3'))
    fig.update_layout(legend_orientation="h",  autosize=True, width=800,
                      height=1000, font=dict(family="Courier New, monospace", size=12))
    py.offline.plot(fig, filename='{}.html'.format(output_dir))


@task
@load_plugin_env_vars("FabCovid19")
def facs_locationplot(output_dir, output_file='covid_out_infections.csv'):
    results_dir = locate_results_dir(output_dir)
    borough = extract_location_name(results_dir)
    
    # Extract cores value
    cores = int(output_dir.split("_")[-1])
    print("CORES = {}".format(cores))

    run_list = []
    for root, dirs, files in os.walk(results_dir, topdown=True):
        # print(root,dirs,files)
        for name in files:
            if "covid_out_infections_" in name and borough in root:
                replica = root.split('\\')[-1].split('_')[1]
                filepath = os.path.join(root, name)
                print("file found at:", filepath)
                df = pd.read_csv(filepath, usecols=[
                                 '#time', 'x', 'y', 'location_type'])
                run_list.append(df)

    print("INFO: {} files read, representing {} runs.".format(len(run_list), len(run_list)/cores))
    # Calculate ensemble size
    runs = int(len(run_list)/cores)

    rows = []
    no = 0
    for df in run_list:
        grouped = df.groupby(['#time', 'location_type'])
        for name, group in grouped:
            d = {'time': name[0], 'run': no,
                 'type': name[1], 'count': len(group)}
            rows.append(d)
        no += 1

    types = ['hospital', 'house', 'office', 'park', 'leisure',
             'school', 'supermarket', 'shopping', 'traffic']
    pdf = pd.DataFrame(rows)
    pdf = pdf[pdf.time != "#t"]
    pdf['time'] = pd.to_numeric(pdf['time'])

    mean_rows = []
    for i in range(pdf['time'].min(), pdf['time'].max()):
        for j in types:
            data = pdf[(pdf['time'] == i) & (pdf['type'] == j)]
            # print(j,data)
            count = data['count'].sum()
            count /= runs
            d = {'time': i, 'type': j, 'mean': count}
            mean_rows.append(d)
    mdf = pd.DataFrame(mean_rows)
    plot(mdf, output_dir, types)
