

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
def validate_facs(cores=1, skip_runs=False, label="", **args):
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
        facs_ensemble("validation", cores=1, **args)

    # if not run locally, wait for runs to complete
    update_environment()
    if env.host != "localhost":
        wait_complete("")
    if skip_runs:
        env.config = "validation"

    fetch_results()

    results_dir = template(env.job_name_template)
    validate_facs_output(results_dir)
