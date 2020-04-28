# -*- coding: utf-8 -*-
#
# This source file is part of the FabSim software toolkit, which is distributed under the BSD 3-Clause license.
# Please refer to LICENSE for detailed information regarding the licensing.
#
# This file contains FabSim definitions specific to FabCovid19.
#
# authors: Hamid Arabnejad, Derek Groen

from base.fab import *
import shutil
import pandas as pd
from os import makedirs, path, walk
import csv
from pprint import pprint

# Add local script, blackbox and template path.
add_local_paths("FabCovid19")


@task
def covid19(location,
            TS,
            TM,
            outdir=".",
            **args):
    """
    parameters:
      - location : [brent,harrow,ealing,hillingdon]
      - TS (Transition Scenario) : [no-measures, extend-lockdown, open-all,
                                    open-schools, open-shopping, open-leisure,
                                    work50, work75, work100]
      - TM (transition Mode) : [1,2,3]
    """

    update_environment(args, {"location": location,
                              "transition_scenario": TS,
                              "transition_mode": TM,
                              "output_dir": outdir
                              })
    with_config(location)
    execute(put_configs, location)
    job(dict(script='Covid19', wall_time='0:15:0', memory='2G'), **args)


@task
def cal_avg_csv(location, TS, TM, **args):

    update_environment(args)
    with_config(location)
    work_dir = path.join(env.local_results,
                         template(env.job_name_template))

    result_PATH = "{}/{}".format(env.local_results,
                                 template(env.job_name_template))

    if not path.exists(result_PATH):
        print('Error : Please check the input parameters')
        print('PATH = %s \t could not be found!!!' % (result_PATH))
        exit()

    # set TD (transition day) based on TM (transition mode)
    TM = int(TM)
    if TM == 1:
        TD = 77  # 15th of April
    if TM == 2:
        TD = 93  # 31st of May
    if TM == 3:
        TD = 108  # 15th of June
    if TM == 4:
        TD = 123  # 30th of June
    if TM > 10:
        TD = TM
    # find all out.csv files from input directory
    csv_file_address = []
    target_csv_name = "{}-{}-{:d}.csv".format(location, TS, TD)
    # r=root, d=directories, f = files
    # search for out.csv in all subdirectories
    li = []
    for r, d, f in walk(result_PATH):
        for file in f:
            if file == target_csv_name:
                #csv_file_address.append(path.join(r, file))
                df = pd.read_csv(path.join(r, file),
                                 index_col=None,
                                 header=0,
                                 sep=',',
                                 encoding='latin1')
                li.append(df)

    # csv_file_address.sort()
    results = pd.concat(li, axis=0, ignore_index=True)
    avg_results = results.groupby(['#time']).mean().round(0).astype(int)

    result_avg_PATH = "{}/{}/{}-{}-avg".format(env.local_results,
                                               template(env.job_name_template),
                                               TS, env.cores)
    avg_csv_name = "{}-{}-{:d}.csv".format(location, TS, TD)
    if not os.path.exists(result_avg_PATH):
        makedirs(result_avg_PATH)

    avg_results.to_csv(path.join(result_avg_PATH, avg_csv_name),
                       sep=',')


@task
def covid19_ensemble(location,
                     TS=None,
                     TM=None,
                     outdir=".",
                     script='Covid19',
                     ** args):
    '''
    run an ensemble of Covid-19 simulation
      fab <machine> covid19_ensemble:location='brent;harrow;hillingdon'
      fab <machine> covid19_ensemble:location='brent;harrow;hillingdon'

    '''
    location = location.split(';')

    if not (TS is None):
        TS = TS.split(';')
    else:
        TS = ['no-measures', 'extend-lockdown', 'open-all', 'open-schools',
              'open-shopping', 'open-leisure', 'work50', 'work75', 'work100',
              'dynamic-lockdown']

    if not (TM is None):
        TM = [int(s) if s.isdigit() else -1 for s in TM.split(';')]
    else:
        TM = [1, 2, 3, 4]

    count = 0
    for loc in location:

        update_environment(args, {"location": loc,
                                  "transition_scenario": '',
                                  "transition_mode": '-1',
                                  "output_dir": outdir
                                  })
        # with_config(loc)
        path_to_config = find_config_file_path(loc)
        sweep_dir = path_to_config + "/SWEEP"

        # clear SWEEP folder for target scenario
        shutil.rmtree(sweep_dir, ignore_errors=True)
        makedirs(sweep_dir)

        for transition_scenario in TS:
            for transition_mode in TM:
                if transition_scenario in ['no-measures', 'extend-lockdown'] \
                        and transition_mode != 1:
                    continue
                count = count + 1
                base_csv_folder = os.path.join(sweep_dir, "{}-{:d}".format(transition_scenario,
                                                                           transition_mode))
                makedirs(base_csv_folder)
                with open(os.path.join(base_csv_folder, 'simsetting.csv'), 'w') as f:
                    f.write('"transition_scenario","%s"\n' %
                            (transition_scenario))
                    f.write('"transition_mode",%d' %
                            (transition_mode))

        env.script = script
        run_ensemble(loc, sweep_dir, **args)
