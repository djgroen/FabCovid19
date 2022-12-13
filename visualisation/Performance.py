import sys
import os
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

from plugins.FabCovid19.FabCovid19 import *
from .facs_postprocess_utils import *


@task
@load_plugin_env_vars("FabCovid19")
def facs_performance(regions, machine, cores, mode):

    cores = cores.split(';')
    regions = regions.split(';')

    if ';' in machine:
        sys.exit('Only one machine allowed in performance analysis. But {} were given'.format(len(machine.split(';'))))

    if mode == 'speedup':
        flag = True
    elif mode == 'time':
        flag = False
    else:
        sys.exit('mode must be either speedup or time...')

    fig, ax = plt.subplots(figsize=(10,10))

    for region in regions:

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
                    if len(lines) == 0:
                        sys.exit('File {} not found'.format(ff))
                    last_line = lines[-1]
                
                times.append(last_line.split(' ')[-2])

            for ii in range(len(times)):
                tt = times[ii]
                try:
                    float(tt)
                except ValueError:
                    sys.exit('Siimulation in file {} has not completed'.format(file_list[ii]))
                Cores.append(int(cc))
                Times.append(float(tt))

        Speedup = [Times[0]/x for x in Times]

        mean_time = []
        mean_speedup = []

        for cc in cores:

            tt = [Times[i] for i in range(len(Times)) if int(cc) == Cores[i]]
            ss = [Speedup[i] for i in range(len(Speedup)) if int(cc) == Cores[i]]

            mean_time.append(sum(tt)/len(tt))
            mean_speedup.append(sum(ss)/len(tt))

        cores = [int(x) for x in cores]

        if flag:
            ax.loglog(cores, mean_speedup, '.-')
            ax.loglog(Cores, Speedup, '.')
        else:
            ax.loglog(cores, mean_time, '.-')
            ax.loglog(Cores, Times, '.')
            
        print('{}\nCore\t\tTime'.format(region))
        for ii in range(len(cores)):
            print('{}\t\t{}'.format(cores[ii], mean_time[ii]))
        
    plt.show()