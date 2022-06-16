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
from pathlib import Path

from plugins.FabCovid19.FabCovid19 import *
from .facs_postprocess_utils import *

titles = {
    'susceptible': 'No. of susceptible people over time',
    'exposed': 'No. of exposed people over time',
    'infectious': 'No. of infected people over time',
    'recovered': 'No. of recoveries over time',
    'dead': 'Cumulative no. of deaths over time',
    'immune': 'No. of immune people over time',
    'num infections today': 'No. of infections over time',
    'num hospitalisations today': 'No. of hospitalisations over time',
    'hospital bed occupancy': 'Hospital bed occupancy over time',
    'num hospitalisations today (data)': 'No. of hospitalisations over time according to data',
    'cum num hospitalisations today': 'Cumulative no. of hospitalisations over time',
    'cum num infections today': 'Cumulative no. of infections over time'
}

def get_region(fname):

    base = len(env.local_results.split('/'))
    return fname.split('/')[-4].split('_')[0]

def get_population(region):

    age_file = '{}/config_files/{}/covid_data/age-distr.csv'.format(env.localplugins["FabCovid19"], region)
    df = pd.read_csv(age_file)
    return df[region].sum()

def create_plot(df, title):

    fig = go.Figure([
        go.Scatter(
            name='mean',
            x=df['date'],
            y=df['mean'],
            mode='lines',
            # line=dict(color='rgb(31, 119, 180)'),
        ),
        go.Scatter(
            name='Upper Bound',
            x=df['date'],
            y=df['mean']+df['std'],
            mode='lines',
            marker=dict(color="#444"),
            line=dict(width=0),
            showlegend=False
        ),
        go.Scatter(
            name='Lower Bound',
            x=df['date'],
            y=df['mean']-df['std'],
            marker=dict(color="#444"),
            line=dict(width=0),
            mode='lines',
            fillcolor='rgba(68, 68, 68, 0.3)',
            fill='tonexty',
            showlegend=False
        ),
    ])
    fig.update_layout(
        yaxis_title='Number per 100,000',
        xaxis_title='Date',
        title=title.title(),
        title_x=0.5,
        hovermode="x"
    )
    # fig.write_image('Combine_NW_hospitalisation.png')
    fig.show()

def filter_data(region, machine, cores, measures, runs):

    region = region.split(';')
    machine = machine.split(';')
    cores = cores.split(';')
    measures = measures.split(';')
    runs = runs.split(';')

    base = len(env.local_results.split('/'))

    ll = Path(env.local_results).rglob('*')
    ll = [str(p) for p in ll]

    ll = [x for x in ll if len(x.split('/')) == base + 4 and x.split('/')[-1] == 'out.csv' and x.split('/')[-3] == 'RUNS']

    if region != ['all']:
        ll = [x for x in ll if x.split('/')[-4].split('_')[0] in region]

    if machine != ['all']:
        ll = [x for x in ll if x.split('/')[-4].split('_')[1] in machine]

    if cores != ['all']:
        ll = [x for x in ll if x.split('/')[-4].split('_')[2] in cores]

    if measures != ['all']:
        ll = [x for x in ll if '_'.join(x.split('/')[-2].split('_')[:-1]) in measures]

    if runs != ['all']:
        ll = [x for x in ll if x.split('/')[-2].split('_')[-1] in runs]

    return ll

def compute_mean(variables,files):

    vs = []

    for vv in variables:

        if vv not in titles.keys():
            print('Skipping unknown variable {}'.format(vv))
            continue
    
        df = pd.DataFrame()

        ii = 1

        for ff in files:

            pop = get_population(get_region(ff))

            dd = pd.read_csv(ff, usecols=[vv])
            if len(list(dd[vv])) == 0:
                print('Run {} corresponding to {} not found'.format(ii, ff))
            else:
                df['Run {}'.format(ii)] = dd

            ii += 1
        
        ss = pd.DataFrame()
        ss['date'] = pd.read_csv(ff, usecols=['date'])
        ss['mean'] = df.mean(axis=1)*100000/pop
        ss['std'] = df.std(axis=1)*100000/pop

        vs.append(ss)

    return vs

def plot(files, variables):

    variables = variables.split(';')
    vs = compute_mean(variables, files)
    for ii in range(len(vs)):
        create_plot(vs[ii], title=titles[variables[ii]])

def select_comparision_instance(base, instance, compare, region, machine, cores, measures, runs):
    if compare == 'region':
        region = base[instance]
    elif compare == 'machine':
        machine = base[instance]
    elif compare == 'cores':
        cores = base[instance]
    elif compare == 'measures':
        measures = base[instance]
    elif compare == 'runs':
        runs = base[instance]

    return [region, machine, cores, measures, runs]

@task
@load_plugin_env_vars("FabCovid19")
def facs_combine(region='all', machine='all', cores='all', measures='all', runs='all', variables='all'):

    files = filter_data(region, machine, cores, measures, runs)

    if variables == 'all':
        variables = ';'.join(list(titles.keys()))

    ss = plot(files, variables)

    return ss

@task
@load_plugin_env_vars("FabCovid19")
def facs_compare(region='all', machine='all', cores='all', measures='all', runs='all', variables='all', compare='all'):

    print(get_population(region))

    if compare not in list(locals().keys()):
        print('Comparision not valid')
        sys.exit()

    if len(locals()[compare].split(';')) > 1:

        base = locals()[compare].split(';')
        variables = variables.split(';')

        for ii in range(len(base)):

            for jj in range(ii+1, len(base)):

                [region, machine, cores, measures, runs] = select_comparision_instance(base, ii, compare, region, machine, cores, measures, runs)
                files1 = filter_data(region=region, machine=machine, cores=cores, measures=measures, runs=runs)
                ss1 = compute_mean(variables, files1)

                [region, machine, cores, measures, runs] = select_comparision_instance(base, jj, compare, region, machine, cores, measures, runs)
                files2 = filter_data(region=region, machine=machine, cores=cores, measures=measures, runs=runs)
                ss2 = compute_mean(variables, files2)

                tt = pd.DataFrame()
                tt['date'] = ss1[0]['date']
                tt['mean'] = ss1[0]['mean']-ss2[0]['mean']
                tt['std'] = ss1[0]['std']+ss2[0]['std']

                create_plot(tt, 'Difference in {} <br> ({} {}-{})'.format(titles[variables[0]], compare, base[ii], base[jj]))