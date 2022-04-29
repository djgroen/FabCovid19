import pandas as pd
import os

def get_region_names():

    path = '../config_files'
    return os.listdir(path)

def get_validation_names():
    path = 'raw_data'
    d = os.listdir(path)
    d = list(set(['_'.join(x.split('_')[:-1]) for x in d]))
    return d


def update_validation_data(regions='all', force=False):

    region_list = get_region_names()
    if regions == 'all':
        validation_region_list = get_validation_names()
    else:
        if isinstance(regions, list):
            validation_region_list = regions
        else:
            validation_region_list = list([regions])

    for region in validation_region_list:

        if region not in region_list:
            print('Region {} not found in config files...'.format(region))
        else:
            print('Region {} found in config files...'.format(region))
            validation_path = '../config_files/' + region +'/covid_data/admissions.csv'
            if os.path.exists(validation_path) and not force:
                print('Validation data for {} already exists.'.format(region))
            else:
                print('Compiling validation data for {}...'.format(region))

                ii = 1

                data_path = 'raw_data/' + region + '_' + str(ii) + '.csv'


                while (os.path.exists(data_path)):

                    data_path = 'raw_data/' + region + '_' + str(ii) + '.csv'

                    if ii == 1:
                        try:
                            df = pd.read_csv(data_path)
                        except:
                            print('Name format wrong')
                        df = df[['date', 'newAdmissions']]
                    else:
                        try:
                            ddf = pd.read_csv(data_path)
                        except:
                            break
                        df['newAdmissions_t'] = ddf['newAdmissions']
                        df['newAdmissions_t'] = df['newAdmissions_t'].fillna(0)
                        df['newAdmissions'] += df['newAdmissions_t']
                        df = df[['date', 'newAdmissions']]
 
                    ii += 1
 
                df['date'] = pd.to_datetime(df['date'])
                df['date'] = df['date'].dt.strftime('%d/%m/%Y')
                df = df.rename(columns={'newAdmissions': 'admissions'})

                df.to_csv(validation_path, index=False)

if __name__ == '__main__':
    update_validation_data(force=True)
    print('Done')