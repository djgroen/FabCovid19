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
from os import makedirs
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
              'open-shopping', 'open-leisure', 'work50', 'work75', 'work100']

    if not (TM is None):
        TM = [int(s) if s.isdigit() else -1 for s in TM.split(';')]
    else:
        TM = [1, 2, 3]

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
