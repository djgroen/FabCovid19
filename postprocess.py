try:
    from fabsim.base.fab import *
except ImportError:
    from base.fab import *

from plugins.FabCovid19.FabCovid19 import *


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
def c19_avg_validate(results_dir, icu_fname="", adm_fname="", sim_out_fname="brent-periodic-lockdown-77.csv"):
    update_environment()
    results_dir = "{}/{}".format(env.local_results, results_dir)
    script_dir = env.localhome + "/covid19-postprocess/validation"
    icu_csv_fname = "{}/validation_data/NPH_ICU_occupancy.csv".format(
        env.covid_postproc_location)
    if len(icu_fname) > 0:
        icu_csv_fname = icu_fname
    adm_csv_fname = "{}/validation_data/NPH_admissions.csv".format(
        env.covid_postproc_location)
    if len(adm_fname) > 0:
        adm_csv_fname = adm_fname

    local("python3 {}/ValidationAvg.py {} {} {} {}".format(script_dir,
                                                           results_dir, adm_csv_fname, icu_csv_fname, sim_out_fname))
