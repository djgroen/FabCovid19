

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
                                         "Error"]))
        return validation_results["totals"]["Error"]

    print("error: vvp_validate_results failed on {}".format(output_dir))
    return -1.0
