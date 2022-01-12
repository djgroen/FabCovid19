# This file contains the function definitions for Verification and Validation
# Patterns (VVP) specific to FACS.
# Pattern-1: Stable Intermediate Forms (SIF)
# Pattern-2: Level of Refinement (LoR)
# Pattern-3: Ensemble Output Validation (EoV)
# Pattern-4: Quantity of Interest (QoI)
#
# author: Hamid Arabnejad
#
try:
    from fabsim.base.fab import *
except ImportError:
    from base.fab import *

try:
    from fabsim.VVP.vvp import ensemble_vvp_LoR
except ImportError:
    from VVP.vvp import ensemble_vvp_LoR

from pprint import pprint
import yaml
import ruamel.yaml
import os
import json
import glob
from shutil import rmtree
import easyvvuq as uq
import chaospy as cp
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats.mstats import gmean
from plugins.FabCovid19.FabCovid19 import *


@task
@load_plugin_env_vars("FabCovid19")
def facs_analyse_vvp_LoR(location, sampler_name=None, ** args):
    """
    facs_analyse_vvp_LoR will analysis the output of each vvp ensemble series

    usage example:
        fab localhost facs_analyse_vvp_LoR:mali
        fab training_hidalgo facs_analyse_vvp_LoR:location=test

    """
    update_environment()

    if len(location.split(';')) > 1:
        raise ValueError(
            "Error, only pass single location and not multiple locations"
        )
        exit()

    ############################################
    # load FACS SA configuration from yml file #
    ############################################
    facs_VVP_config_file = os.path.join(
        get_plugin_path("FabCovid19"),
        "VVP",
        "facs_VVP_config.yml"
    )
    facs_VVP_campaign_config = load_VVP_campaign_config(facs_VVP_config_file)

    polynomial_order_range = range(
        facs_VVP_campaign_config["polynomial_order_range"]["start"],
        facs_VVP_campaign_config["polynomial_order_range"]["end"],
        facs_VVP_campaign_config["polynomial_order_range"]["step"]
    )
    sampler_name = facs_VVP_campaign_config["sampler_name"]

    ###########################################
    # set a default dir to save results sobol #
    ###########################################
    sobol_work_dir = os.path.join(
        get_plugin_path("FabCovid19"),
        "VVP",
        "facs_vvp_LoR_{}".format(sampler_name),
        "sobol"
    )

    ###################################
    # delete sobol_work_dir is exists #
    ###################################
    if os.path.exists(sobol_work_dir):
        rmtree(sobol_work_dir)
    os.makedirs(sobol_work_dir)

    for polynomial_order in polynomial_order_range:
        campaign_name = "facs_vvp_LoR_{}_po{}_".format(
            sampler_name,
            polynomial_order
        )
        campaign_work_dir = os.path.join(
            get_plugin_path("FabCovid19"),
            "VVP",
            "facs_vvp_LoR_{}".format(sampler_name),
            "campaign_po{}".format(polynomial_order)
        )

        load_campaign_files(campaign_work_dir)

        ###################
        # reload Campaign #
        ###################
        db_location = "sqlite:///" + campaign_work_dir + "/campaign.db"
        campaign = uq.Campaign(name=campaign_name, db_location=db_location)
        print("===========================================")
        print("Reloaded campaign {}".format(campaign_name))
        print("===========================================")

        sampler = campaign.get_active_sampler()
        campaign.set_sampler(sampler, update=True)

        ####################################################
        # fetch results from remote machine                #
        # here, we ONLY fetch the required results folders #
        ####################################################
        env.job_desc = "_vvp_LoR_{}_po{}".format(
            sampler_name,
            polynomial_order
        )
        with_config(location)

        job_folder_name = template(env.job_name_template)
        print("fetching results from remote machine ...")
        with hide("output", "running", "warnings"), settings(warn_only=True):
            fetch_results(regex=job_folder_name)
        print("Done\n")

        #####################################################
        # copy ONLY the required output files for analyse,  #
        # i.e., EasyVVUQ.decoders.target_filename           #
        #####################################################
        output_filename = facs_VVP_campaign_config[
            "params"]["out_file"]["default"]
        src = os.path.join(env.local_results, job_folder_name, "RUNS")
        des = campaign.campaign_db.runs_dir()
        print("Syncing output_dir ...")
        # with hide('output', 'running', 'warnings'), settings(warn_only=True):
        local(
            "rsync -pthrz "
            "--include='/*/' "
            "--include='{}' "
            "--exclude='*' "
            "{}/  {} ".format(output_filename, src, des)
        )
        print("Done ...\n")

        #######################################
        # Create an decoder for data analysis #
        #######################################
        output_column = facs_VVP_campaign_config["decoder_output_column"]
        decoder = uq.decoders.SimpleCSV(
            target_filename=output_filename,
            output_columns=[output_column]
        )

        #####################
        # execute collate() #
        #####################
        actions = uq.actions.Actions(
            uq.actions.Decode(decoder)
        )
        campaign.replace_actions(campaign_name, actions)
        campaign.execute().collate()
        collation_result = campaign.get_collation_result()

        ##################################################
        # save dataframe containing all collated results #
        ##################################################
        collation_result.to_csv(
            os.path.join(campaign_work_dir, "collation_result.csv"),
            index=False
        )
        collation_result.to_pickle(
            os.path.join(campaign_work_dir, "collation_result.pickle")
        )

        ###################################
        #    Post-processing analysis     #
        ###################################

        if sampler_name == "SCSampler":
            analysis = uq.analysis.SCAnalysis(
                sampler=campaign._active_sampler,
                qoi_cols=[output_column]
            )
        elif sampler_name == "PCESampler":
            analysis = uq.analysis.PCEAnalysis(
                sampler=campaign._active_sampler,
                qoi_cols=[output_column]
            )

        campaign.apply_analysis(analysis)
        results = campaign.get_last_analysis()

        campaign.apply_analysis(analysis)
        results = campaign.get_last_analysis()

        ###################
        #    Plotting     #
        ###################
        fig_desc = "polynomial_order = {}, num_runs = {}, sampler = {}".format(
            polynomial_order,
            campaign.campaign_db.get_num_runs(),
            sampler_name
        )
        props = dict(boxstyle="round", facecolor="wheat", alpha=0.5)

        ########################
        #    Plot raw data     #
        ########################
        output_files = glob.glob(
            os.path.join(campaign_work_dir + "/**/%s" % (output_filename)),
            recursive=True
        )

        fig, ax = plt.subplots()
        ax.set_xlabel("days")
        ax.set_ylabel(output_column)
        fig.suptitle(
            "RAW data : column {}\n".format(output_column),
            fontsize=10, fontweight="bold"
        )
        ax.set_title(
            fig_desc, fontsize=8, loc="center",
            fontweight="bold", bbox=props
        )
        for output_file in output_files:
            total_errors = pd.read_csv(output_file)[
                output_column].values.tolist()
            ax.plot(total_errors)

        plot_file_name = "raw[{}]".format(output_column)
        plt.savefig(os.path.join(campaign_work_dir, plot_file_name),
                    dpi=400)

        ###################################
        #    Plot statistical_moments     #
        ###################################
        fig, ax = plt.subplots()
        ax.set_xlabel("days")
        ax.set_ylabel("velocity {}".format(output_column))
        fig.suptitle(
            "code mean +/- standard deviation\n",
            fontsize=10, fontweight="bold"
        )
        ax.set_title(
            fig_desc, fontsize=8, loc="center",
            fontweight="bold", bbox=props
        )

        mean = results.describe(output_column, "mean")
        std = results.describe(output_column, "std")
        X = range(len(mean))
        ax.plot(X, mean, "b-", label="mean")
        ax.plot(X, mean - std, "--r", label="+1 std-dev")
        ax.plot(X, mean + std, "--r")
        ax.fill_between(X, mean - std, mean + std, color="r", alpha=0.2)
        # plt.tight_layout()
        plt.legend(loc="best")
        plot_file_name = "plot_statistical_moments[{}]".format(output_column)
        plt.savefig(os.path.join(campaign_work_dir, plot_file_name),
                    dpi=400)

        ###################################
        #        Plot sobols_first        #
        ###################################
        fig, ax = plt.subplots()
        ax.set_xlabel("days")
        ax.set_ylabel("Sobol indices")
        fig.suptitle(
            "First order Sobol index [output column = {}]\n".format(
                output_column),
            fontsize=10, fontweight="bold"
        )
        ax.set_title(
            fig_desc, fontsize=8, loc='center',
            fontweight='bold', bbox=props
        )

        sobols_first = results.raw_data["sobols_first"][output_column]
        param_i = 0
        for v in sobols_first:
            y = sobols_first[v].ravel()
            important = False
            if y[-1] != 0:
                ax.plot(y, label=v)
            else:
                print("%s ignored for plotting" % (v))

            param_i = param_i + 1

        plt.legend(loc='best')
        # plt.tight_layout()
        plot_file_name = 'plot_sobols_first[%s]' % (output_column)
        plt.savefig(os.path.join(campaign_work_dir, plot_file_name),
                    dpi=400)

        ###############################################################
        # yml_results contains all campaign info and analysis results #
        # it will be saved in sobols.yml file                         #
        ###############################################################
        S = ruamel.yaml.scalarstring.DoubleQuotedScalarString
        yml_results = ruamel.yaml.comments.CommentedMap()
        yml_results.update({'campaign_info': {}})
        yml_results['campaign_info'].update({
            'name': S(campaign._active_app_name),
            'work_dir': S(campaign.work_dir),
            'num_runs': campaign.campaign_db.get_num_runs(),
            'output_column': S(output_column),
            'polynomial_order': polynomial_order,
            'sampler': S(facs_VVP_campaign_config['sampler_name']),
            'distribution_type': S(facs_VVP_campaign_config['distribution_type']),
            'sparse': S(facs_VVP_campaign_config['sparse']),
            'growth': S(facs_VVP_campaign_config['growth'])
        })
        if sampler_name == 'SCSampler':
            yml_results['campaign_info'].update({
                'quadrature_rule': S(facs_VVP_campaign_config['quadrature_rule']),
                'midpoint_level1': S(facs_VVP_campaign_config['midpoint_level1']),
                'dimension_adaptive': S(facs_VVP_campaign_config
                                        ['dimension_adaptive'])
            })
        elif sampler_name == 'PCESampler':
            yml_results['campaign_info'].update({
                'rule': S(facs_VVP_campaign_config['quadrature_rule']),
            })

        ROUND_NDIGITS = 4
        for param in facs_VVP_campaign_config['selected_vary_parameters']:
            # I used CommentedMap for adding comments
            yml_results[param] = ruamel.yaml.comments.CommentedMap()
            # yml_results.update({param: {}})
            yml_results[param].update({
                "sobols_first_mean":
                    round(float(np.mean(sobols_first[param].ravel())),
                          ROUND_NDIGITS),
                "sobols_first_gmean":
                    round(float(gmean(sobols_first[param].ravel())),
                          ROUND_NDIGITS),
                "sobols_first":
                    np.around(sobols_first[param].ravel(),
                              ROUND_NDIGITS).tolist()
            })
            # add comments to yml
            '''
            yml_results[param].yaml_add_eol_comment(
                "geometric mean, i.e.,  n-th root of (x1 * x2 * … * xn)",
                "sobols_first_gmean")
            yml_results[param].yaml_add_eol_comment(
                "arithmetic mean i.e., (x1 + x2 + … + xn)",
                "sobols_first_mean")
            '''
            yml_results[param].yaml_set_comment_before_after_key(
                "sobols_first_gmean",
                before="geometric mean, i.e., n-th root of (x1 * x2 * … * xn)",
                indent=2)
            yml_results[param].yaml_set_comment_before_after_key(
                "sobols_first_mean",
                before="arithmetic mean i.e., (x1 + x2 + … + xn)/n",
                indent=2)

        yaml = ruamel.yaml.YAML()
        yaml.preserve_quotes = True
        yaml.default_flow_style = None
        # to Prevent long lines getting wrapped in ruamel.yaml
        # we set the yaml.width to a big enough value to prevent line-wrap
        yaml.width = sys.maxsize

        res_file_name = os.path.join(campaign_work_dir, 'sobols.yml')
        print(res_file_name)
        with open(res_file_name, 'w') as outfile:
            yaml.dump(yml_results, outfile)
            '''
            yaml.dump(yml_results, outfile,
                      default_flow_style=None, width=1000)
            '''

        ########################################
        # copy sobols.yml file to sobol folder #
        ########################################
        print("copy sobols.yml file to sobol folder ...")
        # here instead of mkdirs and copy, I used rsync
        local(
            "rsync -pthrz "
            "--include='/*/' "
            "--include='sobols.yml' "
            "--include='*.png' "
            "--exclude='*' "
            "{}  {} ".format(campaign_work_dir, sobol_work_dir)
        )
        print("Done ...\n")

    #####################################################
    # Check the convergence of the SC Sobols indices    #
    # with polynomial refinement                        #
    #####################################################
    ensemble_vvp_LoR(
        results_dirs_PATH=sobol_work_dir,
        load_QoIs_function=load_QoIs_function,
        aggregation_function=plot_convergence,
        plot_file_path=sobol_work_dir
    )


@task
@load_plugin_env_vars("FabCovid19")
def facs_init_vvp_LoR(location,
                      ci_multiplier=0.475,
                      outdir=".",
                      script="Covid19",
                      facs_script="run.py",
                      quicktest="true",
                      transition_scenario=None,
                      sampler_name=None,
                      ** args):
    """
    Level of Refinement (LoR) is a general verification pattern that seeks
    asymptotic behaviour in QoI upon increasing the resolution of certain
    model parameters. It is important to note that the same quantity of
    interest is computed at every given resolution.

    facs_init_vvp_LoR will submit a series of ensemble job
        for each ensemble job, different polynomial_order used to
        generated an EasyVVUQ campaign run set

    usage example:

    fab localhost facs_init_vvp_LoR:location=test
    fab training_hidalgo facs_init_vvp_LoR:location=test,PJ=True
    fab training_hidalgo facs_init_vvp_LoR:location=brent,PJ=True,venv=True

    """
    update_environment()

    if len(location.split(';')) > 1:
        raise ValueError(
            "Error, only pass single location and not multiple locations"
        )
        exit()

    ############################################
    # load FACS SA configuration from yml file #
    ############################################
    facs_VVP_config_file = os.path.join(
        get_plugin_path("FabCovid19"),
        "VVP",
        "facs_VVP_config.yml"
    )
    facs_VVP_campaign_config = load_VVP_campaign_config(facs_VVP_config_file)

    polynomial_order_range = range(
        facs_VVP_campaign_config["polynomial_order_range"]["start"],
        facs_VVP_campaign_config["polynomial_order_range"]["end"],
        facs_VVP_campaign_config["polynomial_order_range"]["step"]
    )
    sampler_name = facs_VVP_campaign_config["sampler_name"]

    #####################################################
    # check user input argument for transition scenario #
    #####################################################
    AcceptableTransitionScenario = [
        "no-measures", "extend-lockdown", "open-all", "open-schools",
        "open-shopping", "open-leisure", "work50", "work75", "work100",
        "dynamic-lockdown", "periodic-lockdown", "uk-forecast"
    ]

    if transition_scenario is not None:
        if transition_scenario not in AcceptableTransitionScenario:
            raise RuntimeError(
                "\nThe input transition scenario, {} , is not VALID"
                "\nThe acceptable inputs are : [{}]".format(
                    transition_scenario,
                    AcceptableTransitionScenario
                )
            )
        else:
            facs_SA_campaign_config["params"]["transition_scenario_index"][
                "default"] = AcceptableTransitionScenario.index(
                transition_scenario
            )

    for polynomial_order in polynomial_order_range:
        campaign_name = "facs_vvp_LoR_{}_po{}_".format(
            sampler_name,
            polynomial_order
        )
        campaign_work_dir = os.path.join(
            get_plugin_path("FabCovid19"),
            "VVP",
            "facs_vvp_LoR_{}".format(sampler_name),
            "campaign_po{}".format(polynomial_order)
        )

        runs_dir, campaign_dir = init_facs_VVP_campaign(
            campaign_name=campaign_name,
            campaign_config=facs_VVP_campaign_config,
            polynomial_order=polynomial_order,
            campaign_work_dir=campaign_work_dir
        )

        ############################################
        # update the FACS simulation env variables #
        ############################################
        update_environment(args, {"script": script,
                                  "facs_script": facs_script
                                  })

        set_facs_args_list(args, {"location": location,
                                  "transition_scenario": '',
                                  "transition_mode": '-1',
                                  "output_dir": outdir,
                                  "ci_multiplier": ci_multiplier,
                                  "quicktest": quicktest,
                                  })

        #############################################################
        # copy the EasyVVUQ campaign run set TO config SWEEP folder #
        #############################################################
        campaign2ensemble(location, campaign_dir)

        ###########################################################
        # set job_desc to avoid overwriting with previous SA jobs #
        ###########################################################
        env.job_desc = "_vvp_LoR_{}_po{}".format(
            sampler_name,
            polynomial_order
        )
        env.prevent_results_overwrite = "delete"
        with_config(location)
        execute(put_configs, location)

        ##########################################
        # submit ensemble jobs to remote machine #
        ##########################################
        path_to_config = find_config_file_path(location)
        sweep_dir = path_to_config + "/SWEEP"
        run_ensemble(location, sweep_dir, **args)


def init_facs_VVP_campaign(campaign_name, campaign_config,
                           polynomial_order, campaign_work_dir):
    ######################################
    # delete campaign_work_dir is exists #
    ######################################
    if os.path.exists(campaign_work_dir):
        rmtree(campaign_work_dir)
    os.makedirs(campaign_work_dir)

    #####################
    # Create an encoder #
    #####################
    directory_tree = {"covid_data": None}

    encoder = uq.encoders.MultiEncoder(
        uq.encoders.DirectoryBuilder(tree=directory_tree),
        uq.encoders.GenericEncoder(
            template_fname=get_plugin_path("FabCovid19") +
            "/templates/template_disease_covid19",
            delimiter="$",
            target_filename="covid_data/disease_covid19.yml"
        ),
        CustomEncoder(
            template_fname=get_plugin_path("FabCovid19") +
            "/templates/template_simsetting",
            delimiter="$",
            target_filename="simsetting.csv"
        ),
    )

    ###########################
    # Set up a fresh campaign #
    ###########################
    db_location = "sqlite:///" + campaign_work_dir + "/campaign.db"
    actions = uq.actions.Actions(
        uq.actions.CreateRunDirectory(root=campaign_work_dir, flatten=True),
        uq.actions.Encode(encoder),
    )

    campaign = uq.Campaign(
        name=campaign_name,
        db_location=db_location,
        work_dir=campaign_work_dir
    )

    ###############################
    # Add the facs-SA-Sampler app #
    ###############################
    campaign.add_app(
        name=campaign_name,
        params=campaign_config["params"],
        actions=actions
    )

    ######################
    # parameters to vary #
    ######################
    vary = {}
    for param in campaign_config["selected_vary_parameters"]:
        lower_value = campaign_config[
            "vary_parameters_range"][param]["range"][0]
        upper_value = campaign_config[
            "vary_parameters_range"][param]["range"][1]
        if campaign_config["distribution_type"] == "DiscreteUniform":
            vary.update({param: cp.DiscreteUniform(lower_value, upper_value)})
        elif campaign_config["distribution_type"] == "Uniform":
            vary.update({param: cp.Uniform(lower_value, upper_value)})

    ####################
    # create Sampler #
    ####################
    sampler_name = campaign_config["sampler_name"]
    if sampler_name == "SCSampler":
        sampler = uq.sampling.SCSampler(
            vary=vary,
            polynomial_order=polynomial_order,
            quadrature_rule=campaign_config["quadrature_rule"],
            growth=campaign_config["growth"],
            sparse=campaign_config["sparse"],
            midpoint_level1=campaign_config["midpoint_level1"],
            dimension_adaptive=campaign_config["dimension_adaptive"]
        )
    elif sampler_name == "PCESampler":
        sampler = uq.sampling.PCESampler(
            vary=vary,
            polynomial_order=polynomial_order,
            rule=campaign_config["quadrature_rule"],
            sparse=campaign_config["sparse"],
            growth=campaign_config["growth"]
        )
    # TODO: add other sampler here

    ###########################################
    # Associate the sampler with the campaign #
    ###########################################
    campaign.set_sampler(sampler)

    #########################################
    # draw all of the finite set of samples #
    #########################################
    campaign.execute().collate()

    #########################################
    # extract generated runs id by campaign #
    #########################################
    runs_dir = []
    for _, run_info in campaign.campaign_db.runs(
            status=uq.constants.Status.NEW
    ):
        runs_dir.append(run_info["run_name"])

    campaign_dir = campaign.campaign_db.campaign_dir()

    ######################################################
    # backup campaign files, i.e, *.db, *.json, *.pickle #
    ######################################################
    backup_campaign_files(campaign.work_dir)

    print("=" * 50)
    print("With user's specified parameters for {}".format(sampler_name))
    print("campaign name : {}".format(campaign_name))
    print("number of generated runs : {}".format(len(runs_dir)))
    print("campaign dir : {}".format(campaign_work_dir))
    print("=" * 50)

    return runs_dir, campaign_dir


def load_VVP_campaign_config(facs_VVP_config_file):
    facs_VVP_campaign_config = yaml.load(
        open(facs_VVP_config_file),
        Loader=yaml.SafeLoader
    )

    #####################################################
    # load parameter space for the easyvvuq sampler app #
    #####################################################
    sampler_params_json_PATH = os.path.join(get_plugin_path("FabCovid19"),
                                            "templates",
                                            "params.json"
                                            )
    sampler_params = json.load(open(sampler_params_json_PATH))

    #########################################################
    # add loaded campaign params to facs_VVP_campaign_config #
    #########################################################
    facs_VVP_campaign_config.update({"params": sampler_params})

    return facs_VVP_campaign_config


def load_QoIs_function(result_dir):
    """
    we load input sobols.yml with this structure:
    vary_param_1:
        sobols_first: <array[....]>
        sobols_first_gmean: <value>
        sobols_first_mean: <value>
    ...
    vary_param_N:
        sobols_first: <array[....]>
        sobols_first_gmean: <value>
        sobols_first_mean: <value>
    campaign_info:
        distribution_type: <str>
        name: <str> # name of campaign
        num_runs: <int>
        polynomial_order: <int>
        sampler: <str> # name of sampler
        work_dir: <str> # PATH to this campaign result

    The returns values are : QoIs_values,polynomial_order
        In this implementation, QoIs_values has this
    vary_param_1:
        score: <value>
    ...
    vary_param_N:
        score: <value>
    """
    data_file_name = os.path.join(result_dir, "sobols.yml")
    sobols_data = yaml.load(open(data_file_name), Loader=yaml.SafeLoader)
    polynomial_order = sobols_data["campaign_info"]["polynomial_order"]
    num_runs = sobols_data["campaign_info"]["num_runs"]
    del sobols_data["campaign_info"]

    # sobols_first_mean or sobols_first_gmean
    score_column_name = "sobols_first_mean"

    QoIs_values = {}
    for param in sobols_data:
        QoIs_values.update({param: {}})
        for key in sobols_data[param]:
            if key == score_column_name:
                QoIs_values[param].update({
                    key: sobols_data[param][key]
                })

    return QoIs_values, polynomial_order, num_runs


def plot_convergence(scores, plot_file_path):
    """
    The VVP agregation_function, compares the sobol indices (as function of
    the polynomial order)
    input scores structure:
    result_dir_1_name:
        order: <polynomial_order>
        value:
            vary_param_1: {<sobol_func_name>:<value>}
            ...
            vary_param_z: {<sobol_func_name>:<value>}
    ...
    result_dir_N_name:
        order: <polynomial_order>
        value:
            vary_param_1: {<sobol_func_name>:<value>}
            ...
            vary_param_z: {<sobol_func_name>:<value>}

    ------------------------------------------------------------------
    NOTE: Here, we use the result with maximum polynomial order as the
        reference value
    """
    last_item_key = list(scores)[-1]

    #############################################
    # ref_sobols_value structure:               #
    #                                           #
    # vary_param_1: {<sobol_func_name>:<value>} #
    # ...                                       #
    # vary_param_n: {<sobol_func_name>:<value>} #
    #############################################
    xticks = []
    ref_sobols_value = scores[last_item_key]["value"]

    results = {}
    results.update({"polynomial_order": []})
    compare_res = {}
    for run_dir in scores:
        polynomial_order = scores[run_dir]["order"]
        num_runs = scores[run_dir]["runs"]
        xticks.append("PO={}\nruns={}".format(polynomial_order, num_runs))
        results["polynomial_order"].append(polynomial_order)
        poly_key = "polynomial_order {}".format(polynomial_order)
        compare_res.update({poly_key: {}})
        for param in scores[run_dir]["value"]:
            if param not in results:
                results.update({param: []})
            sb_func_name = list(scores[run_dir]["value"][param].keys())[0]
            sb = scores[run_dir]["value"][param][sb_func_name]
            results[param].append(sb)

    #############################################
    # plotting results                          #
    # results dict structure                    #
    #       vary_param_1: [run1,run2,...]       #
    #       vary_param_2: [run1,run2,...]       #
    #       polynomial_order: [po1,po2,...]     #
    #############################################

    params = list(results.keys())
    params.remove("polynomial_order")

    fig, ax = plt.subplots()
    ax.set_xlabel("Polynomial Order")
    ax.set_ylabel("sobol indices")
    ax.set_title("convergence", fontsize=10, fontweight="bold")

    X = range(len(results["polynomial_order"]))
    for param in params:
        ax.plot(X, results[param], label=param)

    plt.xticks(X, xticks)
    plt.tight_layout()
    plt.legend(loc="best")
    convergence_plot_file_name = "vvp_QoI_convergence.png"
    plt.savefig(os.path.join(plot_file_path, convergence_plot_file_name),
                dpi=400)

    print("=" * 50)
    print("The convergence plot generated ...")
    print(os.path.join(plot_file_path, convergence_plot_file_name))
    print("=" * 50)


def backup_campaign_files(work_dir_SCSampler):

    backup_dir = os.path.join(work_dir_SCSampler, 'backup')

    # delete backup folder
    if os.path.exists(backup_dir):
        rmtree(backup_dir)
    os.mkdir(backup_dir)

    with hide('output', 'running', 'warnings'), settings(warn_only=True):
        local(
            "rsync -av -m -v \
            --include='*.db' \
            --include='*.pickle' \
            --include='*.json' \
            --exclude='*' \
            {}/  {} ".format(work_dir_SCSampler, backup_dir)
        )


def load_campaign_files(work_dir_SCSampler):

    backup_dir = os.path.join(work_dir_SCSampler, 'backup')

    with hide('output', 'running', 'warnings'), settings(warn_only=True):
        local(
            "rsync -av -m -v \
            --include='*.db' \
            --include='*.pickle' \
            --include='*.json' \
            --exclude='*' \
            {}/  {} ".format(backup_dir, work_dir_SCSampler)
        )


class CustomEncoder(uq.encoders.GenericEncoder):

    def encode(self, params={}, target_dir=''):
        # scale default values found in pre param file

        params["transition_mode"] = round(params["transition_mode"])

        TS = ["no-measures", "extend-lockdown", "open-all", "open-schools",
              "open-shopping", "open-leisure", "work50", "work75", "work100",
              "dynamic-lockdown", "periodic-lockdown", "uk-forecast"]
        index_TS = round(params["transition_scenario_index"])
        params["transition_scenario"] = TS[index_TS]

        super().encode(params, target_dir)
