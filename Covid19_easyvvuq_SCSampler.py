from base.fab import *
import chaospy as cp
import numpy as np
import easyvvuq as uq
import matplotlib.pyplot as plt
import sys
import os
from shutil import rmtree
from pprint import pprint
import json
import time
from plugins.FabCovid19.FabCovid19 import *


# authors: Hamid Arabnejad


# load custom Campaign
from plugins.FabCovid19.customEasyVVUQ import CustomCampaign
uq.Campaign = CustomCampaign
from plugins.FabCovid19.customEasyVVUQ import CustomEncoder


output_column = "num hospitalisations today"


@task
def covid19_init_SC(location,
                    ci_multiplier=0.475,
                    outdir=".",
                    script='Covid19',
                    ** args):
    '''
    ============================================================================
    fab <localhost/remote_machine> covid19_init_SC:location=brent

    Note : for location, only pass single location and not multiple locations

    fab eagle_vecma covid19_init_SC:location=brent
    fab eagle_vecma covid19_init_SC:location=brent,nb_thread=4,PilotJob=True,virtualenv=true
    ============================================================================
    '''

    if len(location.split(';')) > 1:
        print("Error, only pass single location and not multiple locations")
        exit()

    # set work_dir_SCSampler
    work_dir_SCSampler = os.path.join(
        os.path.dirname(__file__),
        'covid19_%s_easyvvuq_SCSampler' % (location)
    )

    # delete work_dir_SCSampler is exists
    if os.path.exists(work_dir_SCSampler):
        rmtree(work_dir_SCSampler)
    os.mkdir(work_dir_SCSampler)

    # Set up a fresh campaign called "covid19-SCSampler"
    campaign = uq.Campaign(name='covid19-SCSampler',
                           work_dir=work_dir_SCSampler)

    # to make sure we are not overwriting the new simulation on previous ones
    job_label = campaign._campaign_dir

    # Define parameter space for the covid19-SCSampler app
    params = json.load(open(os.path.join(get_plugin_path("FabCovid19"),
                                         'templates',
                                         'params.json'
                                         )
                            )
                       )

    output_filename = params["out_file"]["default"]

    # Create an encoder and decoder
    directory_tree = {'covid_data': None}

    encoder = uq.encoders.MultiEncoder(
        uq.encoders.DirectoryBuilder(tree=directory_tree),
        uq.encoders.GenericEncoder(
            template_fname=get_plugin_path("FabCovid19") +
            '/templates/template_disease_covid19',
            delimiter='$',
            target_filename='covid_data/disease_covid19.yml'),
        CustomEncoder(
            template_fname=get_plugin_path("FabCovid19") +
            '/templates/template_simsetting',
            delimiter='$',
            target_filename='simsetting.csv'),

    )

    decoder = uq.decoders.SimpleCSV(target_filename=output_filename,
                                    output_columns=[output_column],
                                    header=0)

    # Create a collation element for this campaign
    collater = uq.collate.AggregateSamples(average=False)

    # Add the covid19-SCSampler app
    campaign.add_app(name="covid19-SCSampler",
                          params=params,
                          encoder=encoder,
                          decoder=decoder,
                          collater=collater)

    # parameters to vary
    vary = {
        "infection_rate": cp.Uniform(0.0035, 0.14),
        "mortality_period": cp.Uniform(4.0, 16.0),
        "recovery_period": cp.Uniform(4.0, 16.0),
        "mild_recovery_period": cp.Uniform(4.5, 12.5),
        "incubation_period": cp.Uniform(2.0, 6.0),
        "period_to_hospitalisation": cp.Uniform(8.0, 16.0),
        #"transition_mode": cp.Uniform(1, 4),
        #"transition_scenario_index": cp.Uniform(0, 11),
    }

    # create SCSampler
    '''
    sampler = uq.sampling.SCSampler(vary=vary,
                                    polynomial_order=1,
                                    quadrature_rule="G"
                                    )
    '''

    # polynomial_order=6 -> 4865 runs
    # polynomial_order=7 -> 15121 runs
    # polynomial_order=8 -> 44689 runs
    sampler = uq.sampling.SCSampler(vary=vary,
                                    polynomial_order=7,
                                    quadrature_rule="C",
                                    sparse=True,
                                    growth=True,
                                    midpoint_level1=True
                                    )
    # Associate the sampler with the campaign
    campaign.set_sampler(sampler)

    # Will draw all (of the finite set of samples)
    campaign.draw_samples()

    run_ids = campaign.populate_runs_dir()

    # copy generated run folders to SWEEP directory in location folder
    # 1. clean location SWEEP dir
    # 2. copy all generated runs by easyvvuq to location SWEEP folder
    path_to_config = find_config_file_path(location)
    sweep_dir = path_to_config + "/SWEEP"

    if os.path.exists(sweep_dir):
        rmtree(sweep_dir)
    os.mkdir(sweep_dir)

    print('=' * 60 + "\nCopying easyvvuq %d runs to %s SWEEP folder ..." %
          (len(run_ids), location))
    with hide('output', 'running', 'warnings'), settings(warn_only=True):
        local(
            "rsync -av -m -v \
            {}/  {} ".format(os.path.join(campaign.work_dir,
                                          campaign.campaign_dir,
                                          'SWEEP'), os.path.join(sweep_dir))
        )
    print("Done\n" + '=' * 60)

    update_environment(args, {"location": location,
                              "ci_multiplier": ci_multiplier,
                              "transition_scenario": '',
                              "transition_mode": '-1',
                              "output_dir": outdir,
                              "script": script
                              })

    env.partition_name = 'covid'

    # logging for scalability test
    log_submission_csv_file = os.path.join(
        os.path.dirname(__file__), 'log_submission.csv'
    )
    if os.path.isfile(log_submission_csv_file) == False:
        with open(log_submission_csv_file, 'a+') as f:
            f.write("nb_thread,total elapsed jobs submission time (in second)\n")
            f.flush()
    start_time = time.time()

    # to make sure we are not overwriting the new simulation on previous ones
    job_label = campaign._campaign_dir
    env.job_name_template += "_{}".format(job_label)

    # submit ensemble jobs
    run_ensemble(location, sweep_dir, **args)

    elapsed_jobs = time.time() - start_time
    with open(log_submission_csv_file, 'a+') as f:
        f.write("%s,%s\n" % (env.nb_thread, elapsed_jobs))
        f.flush()

    # save campaign and sampler state
    campaign.save_state(os.path.join(
        work_dir_SCSampler, "campaign_state.json"))
    sampler.save_state(os.path.join(
        work_dir_SCSampler, "campaign_sampler.pickle"))

    backup_campaign_files(work_dir_SCSampler)


@task
def covid19_analyse_SC(location, ** args):
    '''
    ============================================================================
    fab <localhost/remote_machine> covid19_analyse_SC:location=brent

    Note : for location, only pass single location and not multiple locations

    fab eagle_vecma covid19_analyse_SC:location=brent
    ============================================================================
    '''

    if len(location.split(';')) > 1:
        print("Error, only pass single location and not multiple locations")
        exit()

    # set work_dir_SCSampler
    work_dir_SCSampler = os.path.join(
        os.path.dirname(__file__),
        'covid19_%s_easyvvuq_SCSampler' % (location)
    )

    for output_column in ["num infections today", "num hospitalisations today", "dead", "recovered", "infectious", "exposed"]:
        load_campaign_files(work_dir_SCSampler)

        # reload Campaign
        campaign = uq.Campaign(state_file=os.path.join(work_dir_SCSampler,
                                                       "campaign_state.json"),
                               work_dir=work_dir_SCSampler
                               )
        print('========================================================')
        print('Reloaded campaign', campaign._campaign_dir)
        print('========================================================')

        sampler = campaign.get_active_sampler()
        # sampler.load_state(os.path.join(work_dir_SCSampler,
        # "campaign_sampler.pickle"))
        campaign.set_sampler(sampler)

        # fetch only the required folder from remote machine
        with_config(location)

        # fetch results from remote machine
        job_label = campaign._campaign_dir
        job_folder_name = template(
            env.job_name_template + "_{}".format(job_label))
        print("fetching results from remote machine ...")
        # with hide('output', 'running', 'warnings'), settings(warn_only=True):
        fetch_results(regex=job_folder_name)
        print("Done\n")

        # copy only output folder into local campaign_dir :)
        src = os.path.join(env.local_results, job_folder_name, 'RUNS')
        des = os.path.join(work_dir_SCSampler, campaign._campaign_dir, 'SWEEP')

        print("Syncing output_dir ...")
        with hide('output', 'running', 'warnings'), settings(warn_only=True):
            local(
                "rsync -av -m -v \
                --include='/*/' \
                --include='out.csv'  \
                --exclude='*' \
                {}/  {} ".format(src, des)
            )
        print("Done\n")

        # read json file
        with open(os.path.join(work_dir_SCSampler, "campaign_state.json"), "r") as infile:
            json_data = json.load(infile)

        # updating db file
        from sqlalchemy import create_engine
        engine = create_engine(json_data['db_location'])

        with engine.connect() as con:
            sql_cmd = "UPDATE app "
            sql_cmd += "SET output_decoder = JSON_SET(output_decoder,'$.state.output_columns[0]','%s')" % (
                output_column)
            result = con.execute(sql_cmd)
            result.close()

        # we have to reload again campaign, I don't know why !!!
        campaign = uq.Campaign(state_file=os.path.join(work_dir_SCSampler,
                                                       "campaign_state.json"),
                               work_dir=work_dir_SCSampler
                               )

        sampler = campaign.get_active_sampler()
        campaign.set_sampler(sampler)

        campaign.collate()

        # Return dataframe containing all collated results
        collation_result = campaign.get_collation_result()

        collation_result.to_csv(os.path.join(work_dir_SCSampler,
                                             'collation_result.csv'
                                             ),
                                index=False
                                )

        # Post-processing analysis
        analysis = uq.analysis.SCAnalysis(
            sampler=campaign._active_sampler,
            qoi_cols=[output_column]
        )
        campaign.apply_analysis(analysis)
        results = campaign.get_last_analysis()

        # --------------------------------------------------------------------------
        #                   Plotting
        # --------------------------------------------------------------------------
        fig = plt.figure(figsize=(16, 7))
        # fig = plt.figure()
        ax1 = fig.add_subplot(121,
                              xlabel="days", ylabel=output_column,
                              )
        ax1.set_title("statistical moments for [%s]" %
                      (output_column), fontsize=14, fontweight='bold')

        mean = results["statistical_moments"][output_column]["mean"]
        std = results["statistical_moments"][output_column]["std"]
        ax1.plot(mean)
        ax1.plot(mean + std, '--r')
        ax1.plot(mean - std, '--r')

        sobols_first = results["sobols_first"][output_column]

        ax2 = fig.add_subplot(122,
                              xlabel="days", ylabel="First order Sobol index",
                              title='First order Sobol index ')

        ax2.set_title("First order Sobol index ",
                      fontsize=14, fontweight='bold')

        param_i = 0
        for v in sobols_first:
            y = sobols_first[v]
            important = False
            if y[-1] != 0:
                ax2.plot(y, label=v)
                print("plotting label %s" % (v))
            else:
                print("%s ignored" % (v))

            param_i = param_i + 1

        x1, x2, y1, y2 = plt.axis()
        plt.axis((x1, x2, -0.1, 1.0))
        ax2.set_ylim([-0.1, 1.0])

        ax2.legend(bbox_to_anchor=(0., 1.3),
                   loc="upper left", borderaxespad=0.)

        plt.tight_layout()
        # plt.show()

        output_file_name = os.path.join(
            work_dir_SCSampler,
            'plot_statistical_moments[%s].png' % (output_column)
        )
        print(output_file_name)
        plt.savefig(output_file_name, dpi=400)


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
