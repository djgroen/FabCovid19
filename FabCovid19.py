# -*- coding: utf-8 -*-
#
# This source file is part of the FabSim software toolkit,
# which is distributed under the BSD 3-Clause license.
# Please refer to LICENSE for detailed information regarding the licensing.
#
# This file contains FabSim definitions specific to FabCovid19.
#
# authors: Hamid Arabnejad, Derek Groen

try:
    from fabsim.base.fab import *
except ImportError:
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
            measures="measures_uk",
            starting_infections="200",
            facs_script="run.py",
            quicktest="false",
            household_size="2.6",
            disease="covid19",
            **args):
    """
    parameters:
      - config : [e.g. brent,harrow,ealing,hillingdon]
      - measures : name of measures input YML file
      - starting_infections : number of infections to seed 20 days prior to simulation start
      - quicktest : use larger house sizes to reduce simulation initialisation time
    """
    update_environment(args, {"facs_script": facs_script})
    with_config(config)

    set_facs_args_list(args, {"location": config,
                              "measures_yml": measures,
                              "starting_infections": starting_infections,
                              "quicktest": quicktest,
                              "household_size": household_size,
                              "disease_yml": "disease_{}".format(disease)
                              })

    execute(put_configs, config)
    job(dict(script='pfacs', wall_time='0:15:0', memory='2G',
             label=measures), args)


@task
@load_plugin_env_vars("FabCovid19")
def pfacs(config,
          measures="measures_uk",
          starting_infections="200",
          facs_script="run.py",
          quicktest="false",
          household_size="2.6",
          disease="covid19",
          **args):
    """
    parameters:
      - config : [brent,harrow,ealing,hillingdon]
      - measures : name of measures input YML file
      - starting_infections : number of infections to seed 20 days prior to simulation start
    """
    update_environment(args, {"facs_script": facs_script})
    with_config(config)

    set_facs_args_list(args, {"location": config,
                              "measures_yml": measures,
                              "starting_infections": starting_infections,
                              "quicktest": quicktest,
                              "household_size": household_size,
                              "disease_yml": "disease_{}".format(disease)
                              })

    execute(put_configs, config)
    print(args)
    job(dict(script='pfacs', wall_time='1:00:0', memory='2G',
             label=measures), args)


@task
@load_plugin_env_vars("FabCovid19")
def covid19_campus(config,
                   measures,
                   quicktest="false",
                   **args):
    covid19(config,
            measures=measures,
            facs_script="run_campus.py",
            quicktest=quicktest,
            **args)


@task
@load_plugin_env_vars("FabCovid19")
def facs_ensemble(config,
                  measures="measures_uk",
                  facs_script="run.py",
                  starting_infections=200,
                   household_size="2.6",
                  quicktest="false",
                  ** args):
    # fab localhost facs_validation
    update_environment(args, {"facs_script": facs_script})

    with_config(config)

    set_facs_args_list(args, {"location": "$current_dir",
                              "measures_yml": measures,
                              "starting_infections": starting_infections,
                              "quicktest": quicktest,
                              "household_size": household_size
                              })
    path_to_config = find_config_file_path(config)
    sweep_dir = path_to_config + "/SWEEP"
    env.script = "pfacs"

    run_ensemble(config, sweep_dir, **args)


@task
@load_plugin_env_vars("FabCovid19")
def covid19_ensemble(configs,
                     measures=None,
                     facs_script="run.py",
                     quicktest="false",
                     starting_infections=200,
                     solver="pfacs",
                     household_size="2.6",
                     disease="covid19",
                     ** args):
    '''
    run an ensemble of Covid-19 simulation
      fab <machine> covid19_ensemble:configs='brent;harrow;hillingdon'
      fab <machine> covid19_ensemble:configs='brent;harrow;hillingdon'

    '''
    configs = configs.split(';')

    if not (measures is None):
        measures = measures.split(';')
    else:
        measures = ['measures_uk']

    print("measures set to: ", measures)

    count = 0
    for loc in configs:
        add_plugin_environment_variable("FabCovid19")
        update_environment(args, {"facs_script": facs_script})
        with_config(loc)
        set_facs_args_list(args, {"location": loc,
                                  "measures": '',
                                  "starting_infections": starting_infections,
                                  "quicktest": quicktest,
                                  "household_size": household_size,
                                  "disease_yml": "disease_{}".format(disease)
                                  })

        path_to_config = find_config_file_path(loc)
        sweep_dir = path_to_config + "/SWEEP"

        # clear SWEEP folder for target scenario
        shutil.rmtree(sweep_dir, ignore_errors=True)
        makedirs(sweep_dir)

        for measure_scenario in measures:
            count = count + 1
            base_csv_folder = os.path.join(sweep_dir, measure_scenario)
            makedirs(base_csv_folder)
            with open(os.path.join(base_csv_folder, 'simsetting.csv'),
                      'w') as f:
                f.write('"measures_yml","%s"\n' %
                        (measure_scenario))

        env.script = solver  # pfacs or Covid19

        run_ensemble(loc, sweep_dir, **args)


@task
@load_plugin_env_vars("FabCovid19")
def covid19_uk_trial_small(measures, partition_name="altair", **args):
    configs = "blackburn_with_darwen;blackpool;buckinghamshire;cheshire_east;cheshire_west_and_chester;cumbria;east_sussex;halton;warrington"
    #configs = "blackpool"
    covid19_ensemble(configs, measures=measures, partition_name=partition_name, **args)


@task
@load_plugin_env_vars("FabCovid19")
def covid19_uk_trial_large(measures, partition_name="altair", **args):
    configs = "berkshire;greater_manchester;hampshire;kent;lancashire;merseyside;oxfordshire;surrey;west_sussex"
    #configs = "cheshire_east;surrey"
    covid19_ensemble(configs, measures=measures, partition_name=partition_name, **args)


@task
@load_plugin_env_vars("FabCovid19")
def covid19_uk_trial_rest(measures, partition_name="altair", **args):
    configs = "berkshire;greater_manchester;halton;cumbria"
    #configs = "cheshire_east;surrey"
    covid19_ensemble(configs, measures=measures, partition_name=partition_name, **args)


@task
@load_plugin_env_vars("FabCovid19")
def covid19_campus_ensemble(configs,
                            measures=None,
                            quicktest="false",
                            ** args):
    covid19_ensemble(configs,
                     measures=measures,
                     facs_script="run_campus.py",
                     quicktest=quicktest,
                     **args)

@task
@load_plugin_env_vars("FabCovid19")
def refresh_local_measures():
    config_path = "{}/config_files".format(env.localplugins["FabCovid19"])
    for config_dir in os.listdir(config_path):
        if config_dir == "facs_validation":
            continue
        print("cp {}/measures/* {}/covid_data/".format(env.localplugins["FabCovid19"], "{}/{}".format(config_path, config_dir)))
        local("cp {}/measures/* {}/covid_data/".format(env.localplugins["FabCovid19"], "{}/{}".format(config_path, config_dir)))


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

    local("rm -rf {}".format(facs_location_local + '/facs/__pycache__'))
    local("rm -rf {}".format(facs_location_local + '/__pycache__'))
    local("rm -rf {}".format(facs_location_local + '/readers/__pycache__'))

    rsync_project(
        local_dir=facs_location_local + '/',
        remote_dir=env.facs_location
    )


def set_facs_args_list(*dicts):
    # Loads in facs arguments. Will ONLY load in arguments that have explicitly specified 
    # defaults in the machines_FabCovid19_user.yml file.

    # update facs args from input arguments
    for adict in dicts:
        for key in env.facs_args.keys():
            if key in adict:
                env.facs_args[key] = adict[key]

    # check for quicktest option
    for adict in dicts:
        if 'debug' in adict and \
            adict['debug'].lower() == 'true' and \
                '--dbg' not in env.facs_args['flags']:
            env.facs_args['flags'].append('--dbg')
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

    print("FACS prepared with args list:", env.facs_args_list)

def set_generator_args_list(dict):
    # Loads in facs arguments. Will ONLY load in arguments that have explicitly specified 
    # defaults in the machines_FabCovid19_user.yml file.

    # update facs args from input arguments
    env.generator_args_list = " --location={} ".format(dict['loc'])

    print("Generator prepared with args list:", env.generator_args_list)


try:
    from plugins.FabCovid19.postprocess import *
    from plugins.FabCovid19.visualisation.ValidateAvg import facs_postprocess
    from plugins.FabCovid19.visualisation.PlotByLocationType import facs_locationplot
    from plugins.FabCovid19.visualisation.LocationMap import facs_locationmap
    from plugins.FabCovid19.visualisation.DataAggregator import facs_combine, facs_compare, facs_uk_validation_nw, facs_uk_validation_se, facs_uk_combined_plotter, facs_uk_county_plotter, facs_uk_compare_measures, facs_doubling_time, facs_lithuania
    from plugins.FabCovid19.visualisation.MapSpread import facs_mapspread
    from plugins.FabCovid19.visualisation.Performance import facs_performance

except:
    exc = sys.exc_info()
    print("Error: failed to import module ({})".format(exc))
    print("The FabCovid19 postprocessing module is not imported as a result.")
    pass

try:
    from plugins.FabCovid19.SA.facs_SA import facs_init_SA
    from plugins.FabCovid19.SA.facs_SA import facs_analyse_SA

    from plugins.FabCovid19.VVP.facs_VVP import facs_init_vvp_LoR
    from plugins.FabCovid19.VVP.facs_VVP import facs_analyse_vvp_LoR
except:
    exc = sys.exc_info()
    print("Error: failed to import settings module ({})".format(exc))
    print("The FabCovid19 EasyVVUQ-based functionalities are not imported as a result.")
    pass

try:
    from plugins.FabCovid19.VVP.facs_VVP_ensemble_validation import *
except:
    exc = sys.exc_info()
    print("Error: failed to import settings module ({})".format(exc))
    print("The FabCovid19 ensemble VVP functionalities are not imported as a result.")
    pass
