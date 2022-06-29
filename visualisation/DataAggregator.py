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
import datetime as dt

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
    return '_'.join(fname.split('/')[-4].split('_')[:-2])

def get_population(region):

    age_file = '{}/config_files/{}/covid_data/age-distr.csv'.format(env.localplugins["FabCovid19"], region)
    df = pd.read_csv(age_file)
    df.columns = df.columns.str.lower()
    return df[region].sum()

def create_trace(df, t=[]):

    t.extend([
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
            y=(df['mean']+df['std']),
            mode='lines',
            marker=dict(color="#444"),
            line=dict(width=0),
            showlegend=False
        ),
        go.Scatter(
            name='Lower Bound',
            x=df['date'],
            y=(df['mean']-df['std']),
            marker=dict(color="#444"),
            line=dict(width=0),
            mode='lines',
            fillcolor='rgba(68, 68, 68, 0.3)',
            fill='tonexty',
            showlegend=False
        )]
    )

    return t

def create_plot(tr, title):

    fig = go.Figure(tr)
    fig.update_layout(
        yaxis_title='Number per 100,000',
        xaxis_title='Date',
        title=title.title(),
        title_x=0.5,
        hovermode="x"
    )
    # fig.write_image('measures_lithuania_2.png')
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
        ll = [x for x in ll if '_'.join(x.split('/')[-4].split('_')[:-2]) in region]

    if machine != ['all']:
        ll = [x for x in ll if x.split('/')[-4].split('_')[-2] in machine]

    if cores != ['all']:
        ll = [x for x in ll if x.split('/')[-4].split('_')[-1] in cores]

    if measures != ['all']:
        ll = [x for x in ll if '_'.join(x.split('/')[-2].split('_')[:-1]) in measures]

    if runs != ['all']:
        ll = [x for x in ll if x.split('/')[-2].split('_')[-1] in runs]

    if len(ll) == 0:
        print('No results found for the query')
        sys.exit()

    return ll

def compute_mean(variables,files):

    vs = []

    for vv in variables:

        if vv not in titles.keys():
            print('Skipping unknown variable {}'.format(vv))
            continue
    
        df = pd.DataFrame()

        ii = 1

        pop = 0

        for ff in files:

            pop += get_population(get_region(ff))
            # print(get_region(ff), get_population(get_region(ff)))

            dd = pd.read_csv(ff, usecols=[vv])
            if len(list(dd[vv])) == 0:
                print('Run {} corresponding to {} not found'.format(ii, ff))
            else:
                df['Run {}'.format(ii)] = dd

            ii += 1

        # print(pop)
        # print(df)
        
        ss = pd.DataFrame()
        ss['date'] = pd.read_csv(ff, usecols=['date'])
        ss['mean'] = df.sum(axis=1)*100000/pop
        ss['std'] = df.sem(axis=1)*100000/pop
        ss['date'] = pd.to_datetime(ss['date'],format="%d/%m/%Y").dt.date
        print(ss)

        vs.append(ss)

    return vs

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
def facs_combine(region='all', machine='all', cores='all', measures='all', runs='all', variables='all', groupbymeasures=False, validation=False):

    files = filter_data(region, machine, cores, measures, runs)

    if variables == 'all':
        variables = ';'.join(list(titles.keys()))

    variables = variables.split(';')

    if groupbymeasures == False:
        tt = []
        vs = compute_mean(variables, files)
        for ii in range(len(vs)):
            tr = create_trace(vs[ii])
            if validation:
                tt.append(tr)
            else:
                create_plot(tr, title=titles[variables[ii]])
    else:
        mm = set('_'.join(f.split('/')[-2].split('_')[:-1]) for f in files)
        print(mm)

    return tt, vs

@task
@load_plugin_env_vars("FabCovid19")
def facs_uk_validation_nw(machine='all', cores='all', measures='all', runs='all'):

    region = 'cheshire_east;cheshire_west_and_chester;halton;warrington;cumbria;greater_manchester;lancashire;blackpool;blackburn_with_darwen;merseyside'
    variables = 'infectious;num hospitalisations today'

    tt, vs = facs_combine(region=region, machine=machine, cores=cores, measures=measures, runs=runs, variables=variables, validation=True)
    tt = tt[0]

    variables = variables.split(';')

    for ii in range(2):
        tr = tt[3*ii:3*(ii+1)]

        if ii == 0:
            df = pd.read_csv('{}/validation/validation_nw_infectious.csv'.format(env.localplugins["FabCovid19"]), usecols=['date', 'newCasesBySpecimenDate'])
            df['date'] = pd.to_datetime(df['date'],format="%Y-%m-%d").dt.date
            df = df.rename(columns={'newCasesBySpecimenDate': 'validation'})
            df = df[::-1]
            df = df[29:29+len(vs[ii])]

        if ii == 1:
            df = pd.read_csv('{}/validation/validation_nw_hospitalisations.csv'.format(env.localplugins["FabCovid19"]), usecols=['date', 'newAdmissions'])
            df['date'] = pd.to_datetime(df['date'],format="%Y-%m-%d").dt.date
            df = df.rename(columns={'newAdmissions': 'validation'})
            df = df[::-1]
            df = df[:len(vs[ii])-18]

        ts = [
            go.Scatter(name='validation',x=df['date'],y=df['validation']*100000/7367456,mode='lines')
            ]

        tr.extend(ts)

        create_plot(tr, title=titles[variables[ii]])

@task
@load_plugin_env_vars("FabCovid19")
def facs_uk_validation_se(machine='all', cores='all', measures='all', runs='all'):

    region = 'berkshire;buckinghamshire;east_sussex;hampshire;kent;oxfordshire;surrey;west_sussex'
    variables = 'infectious;num hospitalisations today'

    tt, vs = facs_combine(region=region, machine=machine, cores=cores, measures=measures, runs=runs, variables=variables, validation=True)
    tt = tt[0]

    variables = variables.split(';')

    for ii in range(2):
        tr = tt[3*ii:3*(ii+1)]

        if ii == 0:
            df = pd.read_csv('{}/validation/validation_se_infectious.csv'.format(env.localplugins["FabCovid19"]), usecols=['date', 'newCasesBySpecimenDate'])
            df['date'] = pd.to_datetime(df['date'],format="%Y-%m-%d").dt.date
            df = df.rename(columns={'newCasesBySpecimenDate': 'validation'})
            df = df[::-1]
            df = df[29:29+len(vs[ii])]

        if ii == 1:
            df = pd.read_csv('{}/validation/validation_se_hospitalisations.csv'.format(env.localplugins["FabCovid19"]), usecols=['date', 'newAdmissions'])
            df['date'] = pd.to_datetime(df['date'],format="%Y-%m-%d").dt.date
            df = df.rename(columns={'newAdmissions': 'validation'})
            df = df[::-1]
            df = df[:len(vs[ii])-18]

        ts = [
            go.Scatter(name='validation',x=df['date'],y=df['validation']*100000/9217265,mode='lines')
            ]

        tr.extend(ts)

        create_plot(tr, title=titles[variables[ii]])

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

                tt.to_csv('~/iccs/brent_hosp_compare.csv')

                create_plot(tt, 'Difference in {} <br> ({} {}-{})'.format(titles[variables[0]], compare, base[ii], base[jj]))