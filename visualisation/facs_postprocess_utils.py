import pandas as pd
import sys
import os
import pathlib
from datetime import datetime
from datetime import timedelta
from pprint import pprint

from plugins.FabCovid19.FabCovid19 import *


@load_plugin_env_vars("FabCovid19")
def locate_results_dir(output_dir):
    # check if the output_dir is exists.
    results_dir = os.path.join(env.local_results, output_dir)
    if not os.path.isdir(results_dir):
        raise RuntimeError(
            "\n\nFabCovid19 Error: The input output_dir = {} does NOT exist in "
            "{} directory.\n"
            "Perhaps you did not fetch the results from the remote machine."
            .format(output_dir, env.local_results)
        )
    return results_dir


def extract_location_name(results_dir):
    # finding the name of borough
    for path in pathlib.Path(results_dir).rglob("*_buildings.csv"):
        return os.path.basename(path).split("_buildings.csv")[0]
