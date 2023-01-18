try:
    import fabsim.VVP.vvp as vvp
except ImportError:
    import VVP.vvp as vvp

from pprint import pprint
import yaml
import ruamel.yaml
import os
from shutil import rmtree
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from plugins.FabCovid19.FabCovid19 import *


def facs_vvp_validate_results(output_dir="", **kwargs):
    """ Extract validation results (no dependencies on FabSim env). """

    facs_location_local = user_config["localhost"].get(
        "facs_location", user_config["default"].get("facs_location"))

    local("python3 %s/validate.py %s "
          "> %s/validation_results.yml"
          % (facs_location_local, output_dir, output_dir))

    with open("{}/validation_results.yml".format(output_dir), 'r') as val_yaml:
        validation_results = yaml.load(val_yaml, Loader=yaml.SafeLoader)

        # TODO: make a proper validation metric using a validation schema.
        print("Validation {}: {}".format(output_dir.split("/")[-1],
                                         validation_results["totals"][
                                         "MAPE"]))
        return validation_results["totals"]["MAPE"]

    print("error: vvp_validate_results failed on {}".format(output_dir))
    return -1.0


def _facs_vvp_sif(output_dir="", sif_dir="", **kwargs):
    """ Extract validation results (no dependencies on FabSim env). """

    facs_location_local = user_config["localhost"].get(
        "facs_location", user_config["default"].get("facs_location"))

    local("python3 %s/compare.py %s %s"
          "> %s/validation_results.yml"
          % (facs_location_local, output_dir, sif_dir, output_dir))

    with open("{}/validation_results.yml".format(output_dir), 'r') as val_yaml:
        validation_results = yaml.load(val_yaml, Loader=yaml.SafeLoader)

        # TODO: make a proper validation metric using a validation schema.
        print("Validation {}: {}".format(output_dir.split("/")[-1],
                                         validation_results["totals"][
                                         "MAPE"]))
        return validation_results["totals"]["MAPE"]

    print("error: vvp_sif failed on {}".format(output_dir))
    return -1.0


@task
@load_plugin_env_vars("FabCovid19")
# Syntax: fabsim localhost
# validate_results:facs_results_directory
def facs_validate_results(output_dir):
    score = vvp_validate_results("{}/{}".format(env.local_results, output_dir))
    print("Validation {}: {}".format(output_dir.split[-1]), score)
    return score


def facs_make_vvp_mean(np_array, **kwargs):
    mean_score = np.mean(np_array)
    print("Mean score: {}".format(mean_score))
    return mean_score


@task
@load_plugin_env_vars("FabCovid19")
def validate_facs_output(results_dir):
    """
    Goes through all the output directories and calculates the validation
    scores.
    """
    vvp.ensemble_vvp("{}/{}/RUNS".format(env.local_results, results_dir),
                     facs_vvp_validate_results,
                     facs_make_vvp_mean)


@task
@load_plugin_env_vars("FabCovid19")
def validate_facs(cores=1, skip_runs=False, label="", sif_mode=False, sif_dir="", **args):
    """
    Runs all the validation test and returns all scores, as well as an average.
    """
    if len(label) > 0:
        print("adding label: ", label)
        env.job_name_template += "_{}".format(label)

    env.prevent_results_overwrite = "delete"

    mode = "serial"
    if int(cores) > 1:
        mode = "parallel"

    if not skip_runs:
        facs_ensemble("facs_validation", cores=cores, **args)

    # if not run locally, wait for runs to complete
    update_environment()
    if env.host != "localhost":
        wait_complete("")
    if skip_runs:
        env.config = "facs_validation"

    fetch_results()

    results_dir = template(env.job_name_template)
    validate_facs_output(results_dir)


# Syntax: fabsim localhost
# validate_results:facs_results_directory
def facs_vvp_sif(output_dir, sif_dir):
    score = _facs_vvp_sif("{}/{}".format(env.local_results,
                                         output_dir), "{}/{}".format(env.local_results, sif_dir))
    print("Validation {}: {}".format(output_dir.split[-1]), score)
    return score


@task
@load_plugin_env_vars("FabCovid19")
def compare_facs_to_sif_output(results_dir, sif_dir, ensemble_mode=True):
    """
    Goes through all the output directories and calculates the validation
    scores.
    """

    if ensemble_mode:
        vvp.compare_sif("{}/{}/RUNS".format(env.local_results, results_dir), "{}/{}/RUNS".format(env.local_results, sif_dir),
                        facs_vvp_sif,
                        facs_make_vvp_mean)
    else:
        vvp.compare_sif("{}/{}".format(env.local_results, results_dir), "{}/{}".format(env.local_results, sif_dir),
                        facs_vvp_sif,
                        facs_make_vvp_mean)


@task
@load_plugin_env_vars("FabCovid19")
def facs_compare_sif(config, cores=1, ensemble_mode=True, skip_runs=False, label="", sif_mode=False, sif_dir="", **args):
    """
    Runs all the validation test and returns all scores, as well as an average.
    """
    if len(label) > 0:
        print("adding label: ", label)
        env.job_name_template += "_{}".format(label)

    env.prevent_results_overwrite = "delete"

    mode = "serial"
    if int(cores) > 1:
        mode = "parallel"

    if not skip_runs:
        if ensemble_mode:
            facs_ensemble(config, cores=1, **args)
        else:
            facs(config, cores=1, **args)

    # if not run locally, wait for runs to complete
    update_environment()
    if env.host != "localhost":
        wait_complete("")
    if skip_runs:
        env.config = config

    fetch_results()

    results_dir = template(env.job_name_template)
    compare_facs_to_sif_output(results_dir, sif_dir, ensemble_mode)
