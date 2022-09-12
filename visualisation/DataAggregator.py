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

def get_run(fname):

    return fname.split('/')[-2].split('_')[-1]

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
        # print(ss)

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
def facs_combine(region='all', machine='all', cores='all', measures='all', runs='all', variables='all', groupbymeasures=False, validation=False, show_plot=True):

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
            elif show_plot:
                create_plot(tr, title=titles[variables[ii]])
    else:
        mm = set('_'.join(f.split('/')[-2].split('_')[:-1]) for f in files)
        print(mm)

    return tt, vs

@task
@load_plugin_env_vars("FabCovid19")
def facs_uk_combined_plotter(region='all',machine='all', cores='all', measures='all', runs='all', show=True):

    variables = 'num infections today;num hospitalisations today'

    if region == 'nw':
        region = 'cheshire_east;cheshire_west_and_chester;halton;warrington;cumbria;greater_manchester;lancashire;blackpool;blackburn_with_darwen;merseyside'
    elif region == 'se':
        region = 'berkshire;buckinghamshire;east_sussex;hampshire;kent;oxfordshire;surrey;west_sussex'
    else:
        print('Invalid region')
        return
    
    files = filter_data(region, machine, cores, measures, runs)

    runs_list = list(set(int(get_run(ff)) for ff in files))
    runs_list.sort()
    runs_list = [str(x) for x in runs_list]

    df_inf = pd.DataFrame()
    df_hos = pd.DataFrame()

    for runs in runs_list:
        tt, vs = facs_combine(region=region, machine=machine, cores=cores, measures=measures, runs=runs, variables=variables, validation=True)

        df_inf['Run {}'.format(runs)] = vs[0]['mean']
        df_hos['Run {}'.format(runs)] = vs[1]['mean']

    df_inf['mean'] = df_inf.mean(axis=1)
    df_hos['mean'] = df_hos.mean(axis=1)

    df_inf['date'] = pd.to_datetime(vs[0]['date'],format="%Y-%m-%d").dt.date
    df_inf = df_inf.set_index('date', drop=True)

    df_hos['date'] = pd.to_datetime(vs[1]['date'],format="%Y-%m-%d").dt.date
    df_hos = df_hos.set_index('date', drop=True)


    if len(region.split(';')) == 10:

        if measures == 'measures_uk_trial_baseline':
            title_inf = 'No. of daily infections in North-West-England <br> with current measures'
            title_hos = 'No. of daily hospitalisations in North-West-England <br> with current measures'
        else:
            title_inf = 'No. of daily infections in North-West-England <br> with Tier 2 measures'
            title_hos = 'No. of daily hospitalisations in North-West-England <br> with Tier 2 measures'

        df = pd.read_csv('{}/validation/validation_nw_infectious.csv'.format(env.localplugins["FabCovid19"]), usecols=['date', 'newCasesBySpecimenDate'])
        df['date'] = pd.to_datetime(df['date'],format="%Y-%m-%d").dt.date
        df = df.rename(columns={'newCasesBySpecimenDate': 'validation'})
        df = df[::-1]
        df = df[29:29+len(vs[0])]
        df = df.set_index('date')

        df_inf['validation'] = df['validation']*100000/7367456

        df = pd.read_csv('{}/validation/validation_nw_hospitalisations.csv'.format(env.localplugins["FabCovid19"]), usecols=['date', 'newAdmissions'])
        df['date'] = pd.to_datetime(df['date'],format="%Y-%m-%d").dt.date
        df = df.rename(columns={'newAdmissions': 'validation'})
        df = df[::-1]
        df = df[:len(vs[1])-18]
        df = df.set_index('date')

        df_hos['validation'] = df['validation']*100000/7367456

    else:
        if measures == 'measures_uk_trial_baseline':
            title_inf = 'No. of daily infections in South-East-England <br> with current measures'
            title_hos = 'No. of daily hospitalisations in South-East-England <br> with current measures'
        else:
            title_inf = 'No. of daily infections in South-East-England <br> with Tier 2'
            title_hos = 'No. of daily hospitalisations in South-East-England <br> with Tier 2'

        df = pd.read_csv('{}/validation/validation_se_infectious.csv'.format(env.localplugins["FabCovid19"]), usecols=['date', 'newCasesBySpecimenDate'])
        df['date'] = pd.to_datetime(df['date'],format="%Y-%m-%d").dt.date
        df = df.rename(columns={'newCasesBySpecimenDate': 'validation'})
        df = df[::-1]
        df = df[29:29+len(vs[0])]
        df = df.set_index('date')

        df_inf['validation'] = df['validation']*100000/9217265

        df = pd.read_csv('{}/validation/validation_se_hospitalisations.csv'.format(env.localplugins["FabCovid19"]), usecols=['date', 'newAdmissions'])
        df['date'] = pd.to_datetime(df['date'],format="%Y-%m-%d").dt.date
        df = df.rename(columns={'newAdmissions': 'validation'})
        df = df[::-1]
        df = df[:len(vs[1])-18]
        df = df.set_index('date')

        df_hos['validation'] = df['validation']*100000/9217265

    df_inf = df_inf.reset_index()
    tr = []
    for cc in df_inf.columns:
        if cc not in ['date', 'mean', 'validation']:
            tr.append(
                go.Scatter(
                    name=cc,
                    x=df_inf['date'],
                    y=df_inf[cc],
                    mode='lines',
                    marker=dict(color='lightgray'),
                    line=dict(width=3),
                    showlegend=False
                )
            )
        elif cc == 'mean':
            if measures == 'measures_uk_trial_baseline':
                name = 'Current measures'
                color = 'darkred'
            else:
                name = 'Tier 2 measures'
                color = 'darkgreen'
            tr.append(
                go.Scatter(
                    name=name,
                    x=df_inf['date'],
                    y=df_inf[cc],
                    mode='lines',
                    marker=dict(color=color),
                    line=dict(width=3),
                    showlegend=True
                )
            )

        elif cc == 'validation':
            tr.append(
                go.Scatter(
                    name='Validation',
                    x=df_inf['date'],
                    y=df_inf[cc],
                    mode='lines',
                    marker=dict(color='darkblue'),
                    line=dict(width=3),
                    showlegend=True
                )
            )

    fig1 = go.Figure(tr)

    fig1.add_vline(x='2020-09-24', line_dash="dash")

    fig1.update_layout(
        title = title_inf,
        # legend_title_text='Legend',
        xaxis_title = 'Date',
        yaxis_title = 'Infections per 100,000 population',
        title_x=0.5,
        hovermode="x",
        font=dict(size=18),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=0.2,
            font=dict(size=12)
        )
    )

    fig1.update_layout({
        'plot_bgcolor': 'rgba(256, 256, 256, 100)',
        'paper_bgcolor': 'rgba(256, 256, 256, 100)',
    })

    fig1.update_xaxes(showline=True, linewidth=2, linecolor='black')
    fig1.update_yaxes(showline=True, linewidth=2, linecolor='black')

    df_hos = df_hos.reset_index()
    tr = []
    for cc in df_hos.columns:
        if cc not in ['date', 'mean', 'validation']:
            tr.append(
                go.Scatter(
                    name=cc,
                    x=df_hos['date'],
                    y=df_hos[cc],
                    mode='lines',
                    marker=dict(color='lightgray'),
                    line=dict(width=3),
                    showlegend=False
                )
            )
        elif cc == 'mean':
            if measures == 'measures_uk_trial_baseline':
                name = 'Current measures'
                color = 'darkred'
            else:
                name = 'Tier 2 measures'
                color = 'darkgreen'
            tr.append(
                go.Scatter(
                    name=name,
                    x=df_hos['date'],
                    y=df_hos[cc],
                    mode='lines',
                    marker=dict(color=color),
                    line=dict(width=3),
                    showlegend=True
                )
            )

        elif cc == 'validation':
            tr.append(
                go.Scatter(
                    name='Validation',
                    x=df_hos['date'],
                    y=df_hos[cc],
                    mode='lines',
                    marker=dict(color='darkblue'),
                    line=dict(width=3),
                    showlegend=True
                )
            )

    fig2 = go.Figure(tr)

    fig2.add_vline(x='2020-09-24', line_dash="dash")

    fig2.update_layout(
        title = title_hos,
        # legend_title_text='Legend',
        xaxis_title = 'Date',
        yaxis_title = 'Hospitalisations per 100,000 population',
        title_x=0.5,
        hovermode="x",
        font=dict(size=18),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=0.2,
            font=dict(size=12)
        )
        )

    fig2.update_layout({
        'plot_bgcolor': 'rgba(256, 256, 256, 100)',
        'paper_bgcolor': 'rgba(256, 256, 256, 100)',
    })

    fig2.update_xaxes(showline=True, linewidth=2, linecolor='black')
    fig2.update_yaxes(showline=True, linewidth=2, linecolor='black')

    if show:
        fig1.show()
        fig2.show()
        fig1.write_image('/home/arindam/UK_Trial_Plots/Inf_{}_{}.png'.format(len(region.split(';')), measures), scale=10)
        fig2.write_image('/home/arindam/UK_Trial_Plots/Hos_{}_{}.png'.format(len(region.split(';')), measures), scale=10)

    return df_inf, df_hos, fig1, fig2

@task
@load_plugin_env_vars("FabCovid19")
def facs_uk_county_plotter(region='all',machine='all', cores='all', measures='all', runs='all', show=True):
    
    variables = 'num infections today;num hospitalisations today'

    if region == 'nw':
        region = 'cheshire_east;cheshire_west_and_chester;cumbria;greater_manchester;lancashire;blackpool;blackburn_with_darwen;merseyside;warrington_and_halton'
    elif region == 'se':
        region = 'berkshire;buckinghamshire;east_sussex;hampshire;kent;oxfordshire;surrey;west_sussex'
    else:
        print('Invalid region')
        return
    
    files = filter_data(region, machine, cores, measures, runs)
    # print(files)

    region_list = list(set(get_region(ff) for ff in files))
    print(region_list)
    region_list.sort()
    region_list = [str(x) for x in region_list]
    print(region_list)

    df_inf = pd.DataFrame()
    df_hos = pd.DataFrame()

    for region in region_list:
        tt, vs = facs_combine(region=region, machine=machine, cores=cores, measures=measures, runs=runs, variables=variables, validation=True)

        df_inf[region] = vs[0]['mean']
        df_hos[region] = vs[1]['mean']

    print(df_inf)
    print(df_hos)

    # fig = px.line(df_inf)
    # fig.show()

    # fig = px.line(df_hos)
    # fig.show()


    pop = sum(get_population(region) for region in region_list)

    df_inf['mean'] = sum(df_inf[region]*get_population(region)/100000 for region in df_inf.columns)*100000/pop
    df_hos['mean'] = sum(df_hos[region]*get_population(region)/100000 for region in df_hos.columns)*100000/pop

    df_inf['date'] = pd.to_datetime(vs[0]['date'],format="%Y-%m-%d").dt.date
    df_inf = df_inf.set_index('date', drop=True)

    df_hos['date'] = pd.to_datetime(vs[1]['date'],format="%Y-%m-%d").dt.date
    df_hos = df_hos.set_index('date', drop=True)


    if len(region_list) == 9:

        print('Test')

        if measures == 'measures_uk_trial_baseline':
            title_inf = 'No. of daily infections in North-West-England <br> with current measures'
            title_hos = 'No. of daily hospitalisations in North-West-England <br> with current measures'
        else:
            title_inf = 'No. of daily infections in North-West-England <br> with Tier 2 measures'
            title_hos = 'No. of daily hospitalisations in North-West-England <br> with Tier 2 measures'

        df = pd.read_csv('{}/validation/validation_nw_infectious.csv'.format(env.localplugins["FabCovid19"]), usecols=['date', 'newCasesBySpecimenDate'])
        df['date'] = pd.to_datetime(df['date'],format="%Y-%m-%d").dt.date
        df = df.rename(columns={'newCasesBySpecimenDate': 'validation'})
        df = df[::-1]
        df = df[29:29+len(vs[0])]
        df = df.set_index('date')

        df_inf['validation'] = df['validation']*100000/7367456

        df = pd.read_csv('{}/validation/validation_nw_hospitalisations.csv'.format(env.localplugins["FabCovid19"]), usecols=['date', 'newAdmissions'])
        df['date'] = pd.to_datetime(df['date'],format="%Y-%m-%d").dt.date
        df = df.rename(columns={'newAdmissions': 'validation'})
        df = df[::-1]
        df = df[:len(vs[1])-18]
        df = df.set_index('date')

        df_hos['validation'] = df['validation']*100000/pop

    else:
        if measures == 'measures_uk_trial_baseline':
            title_inf = 'No. of daily infections in South-East-England <br> with current measures'
            title_hos = 'No. of daily hospitalisations in South-East-England <br> with current measures'
        else:
            title_inf = 'No. of daily infections in South-East-England <br> with Tier 2'
            title_hos = 'No. of daily hospitalisations in South-East-England <br> with Tier 2'

        df = pd.read_csv('{}/validation/validation_se_infectious.csv'.format(env.localplugins["FabCovid19"]), usecols=['date', 'newCasesBySpecimenDate'])
        df['date'] = pd.to_datetime(df['date'],format="%Y-%m-%d").dt.date
        df = df.rename(columns={'newCasesBySpecimenDate': 'validation'})
        df = df[::-1]
        df = df[29:29+len(vs[0])]
        df = df.set_index('date')

        df_inf['validation'] = df['validation']*100000/pop

        df = pd.read_csv('{}/validation/validation_se_hospitalisations.csv'.format(env.localplugins["FabCovid19"]), usecols=['date', 'newAdmissions'])
        df['date'] = pd.to_datetime(df['date'],format="%Y-%m-%d").dt.date
        df = df.rename(columns={'newAdmissions': 'validation'})
        df = df[::-1]
        df = df[:len(vs[1])-18]
        df = df.set_index('date')

        df_hos['validation'] = df['validation']*100000/9217265

    df_inf = df_inf.reset_index()
    tr = []
    for cc in df_inf.columns:
        if cc not in ['date', 'mean', 'validation']:
            tr.append(
                go.Scatter(
                    name=cc,
                    x=df_inf['date'],
                    y=df_inf[cc],
                    mode='lines',
                    marker=dict(color='lightgray'),
                    line=dict(width=3),
                    showlegend=False
                )
            )
        elif cc == 'mean':
            if measures == 'measures_uk_trial_baseline':
                name = 'Current measures'
                color = 'darkred'
            else:
                name = 'Tier 2 measures'
                color = 'darkgreen'
            tr.append(
                go.Scatter(
                    name=name,
                    x=df_inf['date'],
                    y=df_inf[cc],
                    mode='lines',
                    marker=dict(color=color),
                    line=dict(width=3),
                    showlegend=True
                )
            )

        elif cc == 'validation':
            tr.append(
                go.Scatter(
                    name='Validation',
                    x=df_inf['date'],
                    y=df_inf[cc],
                    mode='lines',
                    marker=dict(color='darkblue'),
                    line=dict(width=3),
                    showlegend=True
                )
            )

    fig1 = go.Figure(tr)

    fig1.add_vline(x='2020-09-24', line_dash="dash")

    fig1.update_layout(
        title = title_inf,
        # legend_title_text='Legend',
        xaxis_title = 'Date',
        yaxis_title = 'Infections per 100,000 population',
        title_x=0.5,
        hovermode="x",
        font=dict(size=18),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=0.2,
            font=dict(size=12)
        )
    )

    fig1.update_layout({
        'plot_bgcolor': 'rgba(256, 256, 256, 100)',
        'paper_bgcolor': 'rgba(256, 256, 256, 100)',
    })

    fig1.update_xaxes(showline=True, linewidth=2, linecolor='black')
    fig1.update_yaxes(showline=True, linewidth=2, linecolor='black')

    df_hos = df_hos.reset_index()
    tr = []
    for cc in df_hos.columns:
        if cc not in ['date', 'mean', 'validation']:
            tr.append(
                go.Scatter(
                    name=cc,
                    x=df_hos['date'],
                    y=df_hos[cc],
                    mode='lines',
                    # marker=dict(color='lightgray'),
                    line=dict(width=3),
                    showlegend=True
                )
            )
        # elif cc == 'mean':
        #     if measures == 'measures_uk_trial_baseline':
        #         name = 'Current measures'
        #         color = 'darkred'
        #     else:
        #         name = 'Tier 2 measures'
        #         color = 'darkgreen'
        #     tr.append(
        #         go.Scatter(
        #             name=name,
        #             x=df_hos['date'],
        #             y=df_hos[cc],
        #             mode='lines',
        #             marker=dict(color=color),
        #             line=dict(width=3),
        #             showlegend=True
        #         )
        #     )

        # elif cc == 'validation':
        #     tr.append(
        #         go.Scatter(
        #             name='Validation',
        #             x=df_hos['date'],
        #             y=df_hos[cc],
        #             mode='lines',
        #             marker=dict(color='darkblue'),
        #             line=dict(width=3),
        #             showlegend=True
        #         )
        #     )

    fig2 = go.Figure(tr)

    fig2.add_vline(x='2020-09-24', line_dash="dash")
    # fig2.add_hline(y='9.9', line_dash="dash")
    fig2.add_hline(y='8.8', line_dash="dash")

    fig2.update_layout(
        title = title_hos,
        # legend_title_text='Legend',
        xaxis_title = 'Date',
        yaxis_title = 'Hospitalisations per 100,000 population',
        title_x=0.5,
        hovermode="x",
        font=dict(size=18),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=0.2,
            font=dict(size=12)
        )
        )

    fig2.update_layout({
        'plot_bgcolor': 'rgba(256, 256, 256, 100)',
        'paper_bgcolor': 'rgba(256, 256, 256, 100)',
    })

    fig2.update_xaxes(showline=True, linewidth=2, linecolor='black', range=['2020-08-1','2021-01-15'])
    fig2.update_yaxes(showline=True, linewidth=2, linecolor='black', range=[0,12])

    if show:
        fig1.show()
        fig2.show()
        fig1.write_image('/home/arindam/UK_Trial_Plots/County_Colored_Inf_{}_{}.png'.format(len(region_list), measures), scale=10)
        fig2.write_image('/home/arindam/UK_Trial_Plots/County_Colored_Hos_{}_{}.png'.format(len(region_list), measures), scale=10)

    return df_inf, df_hos, fig1, fig2

@task
@load_plugin_env_vars("FabCovid19")
def facs_uk_compare_measures(machine='all', cores='all', runs='all'):

    legend = {'measures_uk_trial_baseline': 'Current measures', 'measures_uk_tier_two': 'Tier 2 measures'}

    for rr in ['nw', 'se']:
        
        if rr == 'nw':
            region_name = 'North-West-England'
        else:
            region_name = 'South-East-England'

        dfi = pd.DataFrame()
        dfh = pd.DataFrame()
        
        for mm in ['measures_uk_trial_baseline', 'measures_uk_tier_two']:
            df_inf, df_hos, fig1, fig2 = facs_uk_combined_plotter(region=rr, machine=machine, cores=cores, measures=mm, runs=runs, show=False)

            dfi[legend[mm]] = df_inf['mean']
            dfh[legend[mm]] = df_hos['mean']

        # f1 = px.line(dfi, title='Daily infections in {}'.format(region_name))

        tr = []
        f1 = make_subplots(specs=[[{"secondary_y": True}]])
        for cc in dfi.columns:
            if cc not in ['date']:
                if cc == 'Current measures':
                    color = 'darkred'
                else:
                    color = 'darkgreen'
                tr.append(
                    go.Scatter(
                        name=cc,
                        x=df_inf['date'],
                        y=dfi[cc],
                        mode='lines',
                        marker=dict(color=color),
                        line=dict(width=3),
                        showlegend=True
                    )
                )
        for tt in tr:
            f1.add_trace(tt, secondary_y=False)
        f1.add_trace(
                go.Scatter(
                    name='Impact of Tier 2',
                    x=df_inf['date'],
                    y=(dfi['Current measures'] - dfi['Tier 2 measures'])*100/dfi['Current measures'],
                    mode='lines',
                    marker=dict(color='magenta'),
                    line=dict(width=3),
                    showlegend=False,
                ),
                secondary_y=True,
            )
        f1.update_yaxes(range=[0,100], title_text='Relative decrease (%)', title_font_color='magenta', tickfont=dict(color='magenta'), secondary_y=True)
        f1.update_xaxes(range=['2020-8-1','2021-1-15'])
        f1.add_vline(x='2020-09-24', line_dash='dash')

        # f2 = px.line(dfh, title='Daily hospitalisations in {}'.format(region_name))
        tr = []
        f2 = make_subplots(specs=[[{"secondary_y": True}]])
        for cc in dfh.columns:
            if cc not in ['date']:
                if cc == 'Current measures':
                    color = 'darkred'
                else:
                    color = 'darkgreen'
                tr.append(
                    go.Scatter(
                        name=cc,
                        x=df_hos['date'],
                        y=dfh[cc],
                        mode='lines',
                        marker=dict(color=color),
                        line=dict(width=3),
                        showlegend=True,
                    )
                )
        for tt in tr:
            f2.add_trace(tt, secondary_y=False)
        f2.add_trace(
                go.Scatter(
                    name='Impact of Tier 2',
                    x=df_hos['date'],
                    y=(dfh['Current measures'] - dfh['Tier 2 measures'])*100/dfh['Current measures'],
                    mode='lines',
                    marker=dict(color='magenta'),
                    line=dict(width=3),
                    showlegend=False,
                ),
                secondary_y=True,
            )
        f2.update_yaxes(range=[0,100], title_text='Relative decrease (%)', title_font_color='magenta', tickfont=dict(color='magenta'), secondary_y=True)
        f2.update_xaxes(range=['2020-8-1','2021-1-15'])
        f2.add_vline(x='2020-09-24', line_dash='dash')

        f1.update_layout(
            title = 'Daily infections in {}'.format(region_name),
            # legend_title_text='Legend',
            xaxis_title = 'Date',
            yaxis_title = 'Infections per 100,000 population',
            title_x=0.5,
            hovermode="x",
            font=dict(size=18),
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=0.5,
                font=dict(size=12)
                )
            )

        f1.update_layout({
            'plot_bgcolor': 'rgba(256, 256, 256, 100)',
            'paper_bgcolor': 'rgba(256, 256, 256, 100)',
        })

        f1.update_xaxes(showline=True, linewidth=2, linecolor='black')
        f1.update_yaxes(showline=True, linewidth=2, linecolor='black')


        f2.update_layout(
            title = 'Daily hospitalisations in {}'.format(region_name),
            # legend_title_text='Legend',
            xaxis_title = 'Date',
            yaxis_title = 'Hospitalisations per 100,000 population',
            title_x=0.5,
            hovermode="x",
            font=dict(size=18),
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=0.5
                )
            )

        f2.update_layout({
            'plot_bgcolor': 'rgba(256, 256, 256, 100)',
            'paper_bgcolor': 'rgba(256, 256, 256, 100)',
        })

        f2.update_xaxes(showline=True, linewidth=2, linecolor='black')
        f2.update_yaxes(showline=True, linewidth=2, linecolor='black')

        f1.show()
        f1.write_image('/home/arindam/UK_Trial_Plots/Compare_Inf_{}.png'.format(region_name), scale=10)

        f2.show()
        f2.write_image('/home/arindam/UK_Trial_Plots/Compare_Hos_{}.png'.format(region_name), scale=10)

@task
@load_plugin_env_vars("FabCovid19")
def facs_doubling_time(region='all', machine='all', cores='all', measures='all', runs='all', variables='num infections today', n_times=6):

    if region == 'nw':
        region = 'cheshire_east;cheshire_west_and_chester;cumbria;greater_manchester;lancashire;blackpool;blackburn_with_darwen;merseyside;warrington_and_halton'
    elif region == 'se':
        region = 'berkshire;buckinghamshire;east_sussex;hampshire;kent;oxfordshire;surrey;west_sussex'

    region = region.split(';')

    df1 = pd.DataFrame()
    df2 = pd.DataFrame()
    df3 = pd.DataFrame()

    for rr in region:

        tt, vs = facs_combine(region=rr, machine=machine, cores=cores, measures=measures, runs=runs, variables=variables, show_plot=False)
        vs = vs[0][['date', 'mean']]
        vs = vs[206:]

        cc = vs.iloc[0]['mean']
        dd = vs.iloc[0]['date']

        ll = []
        mm = []
        nn = []
        for ii in range(len(vs)):
            if vs.iloc[ii]['mean'] > 2*cc:
                dt = vs.iloc[ii]['date'] - dd
                cc = vs.iloc[ii]['mean']
                dd = vs.iloc[ii]['date']
                ll.append(dt.days)
                mm.append(dd)
                nn.append(cc)

        ll += ['-'] * (n_times - len(ll))
        mm += ['-'] * (n_times - len(mm))
        nn += ['-'] * (n_times - len(nn))
        
        df1[rr] = ll
        df2[rr] = mm
        df3[rr] = nn

    print(df1)
    print(df2)
    print(df3)

    df1.to_csv('se_doubling_time.csv')
    df2.to_csv('se_doubling_date.csv')
    df3.to_csv('se_doubling_infe.csv')

@task
@load_plugin_env_vars("FabCovid19")
def facs_uk_validation_nw(machine='all', cores='all', measures='all', runs='all'):

    region = 'cheshire_east;cheshire_west_and_chester;halton;warrington;cumbria;greater_manchester;lancashire;blackpool;blackburn_with_darwen;merseyside'
    variables = 'num infections today;num hospitalisations today'

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
    variables = 'num infections today;num hospitalisations today'

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

@task
@load_plugin_env_vars("FabCovid19")
def facs_lithuania(scenario):

    if scenario == '1':
        cores1 = '130'
        cores2 = '132'
        title = 'No. of cases with schools open/close'
        legend1 = 'Close'
        legend2 = 'Open'
    elif scenario == '2':
        cores1 = '134'
        cores2 = '136'
        title = 'No. of cases with leisure facilities open/close'
        legend1 = 'Close'
        legend2 = 'Open'
    elif scenario == '3':
        cores1 = '138'
        cores2 = '140'
        title = 'No. of cases with internal movement allowed/forbidden'
        legend1 = 'Forbidden'
        legend2 = 'Allowed'
    else:
        print('Invalid Scenario')
        return

    tt, vs1 = facs_combine(region='klaipeda', machine='archer2', cores=cores1, variables='num infections today', groupbymeasures=False, validation=False, show_plot=False)
    tt, vs2 = facs_combine(region='klaipeda', machine='archer2', cores=cores2, variables='num infections today', groupbymeasures=False, validation=False, show_plot=False)

    fig = make_subplots(
        rows=1, cols=1)

    vs1 = vs1[0]
    vs2 = vs2[0]

    fig.add_trace(
        go.Scatter(x=vs1['date'],
                   y=vs1['mean'],
                   name=legend1,
                   line_shape="spline",
                   legendgroup="group1",
                   line=dict(width=4)),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(x=vs2['date'],
                   y=vs2['mean'],
                   name=legend2,
                   line_shape="spline",
                   legendgroup="group1",
                   line=dict(width=4)),
        row=1,
        col=1
    )

    fig.add_vline(x=dt.datetime(2021,4,15), line_width=3, line_dash="dash")

    fig.update_layout(
        plot_bgcolor='rgb(255,255,255)',
        yaxis_title='Number of cases per 100,000',
        xaxis_title='Date',
        title=title.title(),
        title_x=0.5,
        hovermode="x",
        font=dict(size=36)
        )

    fig.update_layout(legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01
    ))

    fig.update_xaxes(showline=True, linewidth=2, linecolor='black')
    fig.update_yaxes(showline=True, linewidth=2, linecolor='black')


    fig.show()
