from easyvvuq.constants import default_campaign_prefix, Status
from easyvvuq.db.sql import CampaignDB
from easyvvuq.data_structs import CampaignInfo
from easyvvuq import Campaign
from easyvvuq.analysis import SCAnalysis
from easyvvuq.encoders import GenericEncoder
import tempfile
import os
import numpy as np

# authors: Hamid Arabnejad
# I wrote this file to overwrite some functionalities in easyvvuq


class CustomCampaign(Campaign):
    # ----------------------------------------------------------------------
    # changes :
    # send runs_dir='SWEEP' when we call CampaignInfo
    # change location of campaign.db to work directory
    # ----------------------------------------------------------------------

    def init_fresh(self, name, db_type='sql',
                   db_location=None, work_dir='.'):

        # Create temp dir for campaign
        campaign_prefix = default_campaign_prefix
        if name is not None:
            campaign_prefix = name

        campaign_dir = tempfile.mkdtemp(prefix=campaign_prefix, dir=work_dir)

        self._campaign_dir = os.path.relpath(campaign_dir, start=work_dir)

        self.db_location = db_location
        self.db_type = db_type

        if self.db_type == 'sql':
            from easyvvuq.db.sql import CampaignDB
            if self.db_location is None:
                self.db_location = "sqlite:///" + work_dir + "/campaign.db"
                # self.db_location = "sqlite:///" + self.campaign_dir +
                # "/campaign.db"
        else:
            message = (f"Invalid 'db_type' {db_type}. Supported types are "
                       f"'sql'.")
            logger.critical(message)
            raise RuntimeError(message)
        from easyvvuq import __version__
        info = CampaignInfo(
            name=name,
            campaign_dir_prefix=default_campaign_prefix,
            easyvvuq_version=__version__,
            campaign_dir=self.campaign_dir,
            # runs_dir=os.path.join(campaign_dir, 'runs')
            runs_dir=os.path.join(campaign_dir, 'SWEEP')
        )
        self.campaign_db = CampaignDB(location=self.db_location,
                                      new_campaign=True,
                                      name=name, info=info)

        # Record the campaign's name and its associated ID in the database
        self.campaign_name = name
        self.campaign_id = self.campaign_db.get_campaign_id(self.campaign_name)

    # ----------------------------------------------------------------------
    # changes :
    # return generated run_ids when we call populate_runs_dir
    # ----------------------------------------------------------------------

    def populate_runs_dir(self):

        # Get the encoder for this app. If none is set, only the directory structure
        # will be created.
        active_encoder = self._active_app_encoder
        if active_encoder is None:
            logger.warning(
                'No encoder set for this app. Creating directory structure only.')

        run_ids = []

        for run_id, run_data in self.campaign_db.runs(
                status=Status.NEW, app_id=self._active_app['id']):

            # Make directory for this run's output
            os.makedirs(run_data['run_dir'])

            # Encode run
            if active_encoder is not None:
                active_encoder.encode(params=run_data['params'],
                                      target_dir=run_data['run_dir'])

            run_ids.append(run_id)
        self.campaign_db.set_run_statuses(run_ids, Status.ENCODED)
        return run_ids


class CustomEncoder(GenericEncoder, encoder_name='CustomEncoder'):

    def encode(self, params={}, target_dir=''):
        # scale default values found in pre param file

        params["transition_mode"] = round(params["transition_mode"])

        TS = ['no-measures', 'extend-lockdown', 'open-all', 'open-schools',
              'open-shopping', 'open-leisure', 'work50', 'work75', 'work100',
              'dynamic-lockdown', 'periodic-lockdown']
        index_TS = round(params["transition_scenario_index"])
        params["transition_scenario"] = TS[index_TS]

        super().encode(params, target_dir)
