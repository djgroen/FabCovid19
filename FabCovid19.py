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
@load_plugin_env_vars("FabCovid19")
def covid19(config,
            TS,
            TM,
            ci_multiplier="0.475",
            facs_script="run.py",
            quicktest="false",
            **args):
    """
    parameters:
      - config : [brent,harrow,ealing,hillingdon]
      - TS (Transition Scenario) : [no-measures, extend-lockdown, open-all,
                                    open-schools, open-shopping, open-leisure,
                                    work50, work75, work100]
      - TM (transition Mode) : [1,2,3]
    """
    update_environment(args, {"facs_script": facs_script})
    with_config(config)

    set_facs_args_list(args, {"location": config,
                              "transition_scenario": TS,
                              "transition_mode": TM,
                              "ci_multiplier": ci_multiplier,
                              "quicktest": quicktest
                              })

    execute(put_configs, config)
    print(args)
    job(dict(script='Covid19', wall_time='0:15:0', memory='2G',
             label="{}-{}-{}".format(TS, TM, ci_multiplier)), args)


@task
def covid19_campus(config,
                   TS,
                   TM,
                   ci_multiplier="0.475",
                   quicktest="false",
                   **args):
    covid19(config,
            TS=TS,
            TM=TM,
            ci_multiplier=ci_multiplier,
            facs_script="run_campus.py",
            quicktest=quicktest,
            **args)


@task
def covid19_ensemble(configs,
                     TS=None,
                     TM=None,
                     ci_multiplier=0.475,
                     facs_script="run.py",
                     quicktest="false",
                     ** args):
    '''
    run an ensemble of Covid-19 simulation
      fab <machine> covid19_ensemble:configs='brent;harrow;hillingdon'
      fab <machine> covid19_ensemble:configs='brent;harrow;hillingdon'

    '''
    configs = configs.split(';')

    if not (TS is None):
        TS = TS.split(';')
    else:
        TS = ['no-measures', 'extend-lockdown', 'open-all', 'open-schools',
              'open-shopping', 'open-leisure', 'work50', 'work75', 'work100',
              'dynamic-lockdown', 'periodic-lockdown']

    if not (TM is None):
        TM = [int(s) if s.isdigit() else -1 for s in TM.split(';')]
    else:
        TM = [1, 2, 3, 4]

    print("TS set to: ", TS)
    print("TM set to: ", TM)
    print("ci_multiplier set to: ", ci_multiplier)

    count = 0
    for loc in configs:
        add_plugin_environment_variable("FabCovid19")
        update_environment(args, {"facs_script": facs_script})
        with_config(loc)
        set_facs_args_list(args, {"location": loc,
                                  "transition_scenario": '',
                                  "transition_mode": '-1',
                                  "ci_multiplier": ci_multiplier,
                                  "quicktest": quicktest
                                  })

        path_to_config = find_config_file_path(loc)
        sweep_dir = path_to_config + "/SWEEP"

        # clear SWEEP folder for target scenario
        shutil.rmtree(sweep_dir, ignore_errors=True)
        makedirs(sweep_dir)

        for transition_scenario in TS:
            for transition_mode in TM:
                count = count + 1
                base_csv_folder = os.path.join(sweep_dir, "{}-{:d}-{}".format(transition_scenario,
                                                                              transition_mode, ci_multiplier))
                makedirs(base_csv_folder)
                with open(os.path.join(base_csv_folder, 'simsetting.csv'), 'w') as f:
                    f.write('"transition_scenario","%s"\n' %
                            (transition_scenario))
                    f.write('"transition_mode",%d' %
                            (transition_mode))

        env.script = 'Covid19'
        run_ensemble(loc, sweep_dir, **args)


@task
def covid19_campus_ensemble(configs,
                            TS=None,
                            TM=None,
                            ci_multiplier=0.475,
                            quicktest="false",
                            ** args):
    covid19_ensemble(configs,
                     TS=TS,
                     TM=TM,
                     ci_multiplier=ci_multiplier,
                     facs_script="run_campus.py",
                     quicktest=quicktest,
                     **args)


@task
@load_plugin_env_vars("FabCovid19")
def sync_facs():
    """
    Synchronize the Flee version, so that the remote machine has the latest 
    version from localhost.
    """
    update_environment()
    facs_location_local = user_config["localhost"].get(
        "facs_location", user_config["default"].get("facs_location"))

    rsync_project(
        local_dir=facs_location_local + '/',
        remote_dir=env.facs_location
    )


def set_facs_args_list(*dicts):
    # update facs args from input arguments
    for adict in dicts:
        for key in env.facs_args.keys():
            if key in adict:
                env.facs_args[key] = adict[key]

    # check for quicktest option
    for adict in dicts:
        if 'quicktest' in adict and \
            adict['quicktest'].lower() == 'true' and \
                '--quicktest' not in env.facs_args['flags']:
            env.facs_args['flags'].append('--quicktest')

    # create the facs input argument list
    env.facs_args_list = ""
    for key, value in env.facs_args.items():
        if isinstance(value, (list)):
            env.facs_args_list += '  '.join(value)
        else:
            env.facs_args_list += " --%s=%s " % (key, value)


try:
    from plugins.FabCovid19.postprocess import *

    from plugins.FabCovid19.SA.facs_SA import facs_init_SA
    from plugins.FabCovid19.SA.facs_SA import facs_analyse_SA

    from plugins.FabCovid19.VVP.facs_VVP import facs_init_vvp_LoR
    from plugins.FabCovid19.VVP.facs_VVP import facs_analyse_vvp_LoR


except ImportError as exc:
    print("Error: failed to import settings module ({})".format(exc))
    pass
