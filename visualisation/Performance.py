import sys
import os
import plotly.express as px

from plugins.FabCovid19.FabCovid19 import *
from .facs_postprocess_utils import *


@task
@load_plugin_env_vars("FabCovid19")
def facs_performance(region, machine, cores):

    cores = cores.split(';')

    if ';' in region:
        sys.exit('Only one region allowed in performance analysis. But {} were given'.format(len(region.split(';'))))
    if ';' in machine:
        sys.exit('Only one machine allowed in performance analysis. But {} were given'.format(len(machine.split(';'))))

    Cores = []
    Times = []

    for cc in cores:

        file_list = []

        dir = "{}/{}_{}_{}/RUNS".format(env.local_results, region, machine, cc)

        for rr in os.listdir(dir):
            filedir = "{}/{}".format(dir, rr)

            file = list(x for x in os.listdir(filedir) if x.split('.')[-1]=='output')
            for f in file:
                f = "{}/{}".format(filedir, f)
                file_list.append(f)

        times = []

        for ff in file_list:

            with open(ff, 'r') as f:
                lines = f.read().splitlines()
                last_line = lines[-1]
            
            times.append(last_line.split(' ')[-2])

        for tt in times:
            Cores.append(int(cc))
            Times.append(float(tt))

    fig = px.scatter(x=Cores, y=Times,
                    labels={'x': 'Cores', 'y': 'Time required (s)'},
                    log_x=True,
                    log_y=True,
                    )

    fig.update_layout({
            'plot_bgcolor': 'rgba(255, 255, 255, 255)',
            'paper_bgcolor': 'rgba(255, 255, 255, 255)',
            })

    fig.update_xaxes(showline=True, linewidth=2, linecolor='black')
    fig.update_yaxes(showline=True, linewidth=2, linecolor='black')

    fig.show()

