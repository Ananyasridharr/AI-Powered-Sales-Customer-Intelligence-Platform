import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from base_validator import BaseValidator
VALID_SOURCES={'Facebook','Google Ads','Email','Instagram','LinkedIn','YouTube','SMS','TikTok','Affiliate','Display'}
VALID_GOALS={'Brand Awareness','Product Launch','Retargeting','Lead Generation','Seasonal Sale'}
class CampaignDimValidator(BaseValidator):
    def __init__(self, df, engine=None):
        super().__init__(df, 'dim_campaign', engine)
    def validate(self):
        self._check('D1','campaign_id is not null',mask=self.df['campaign_id'].notna())
        self._check('D2','campaign_id is unique',mask=~self.df['campaign_id'].duplicated(keep=False))
        self._check('D3','source is known',mask=self.df['source'].isin(VALID_SOURCES))
        self._check('D4','goal is known',mask=self.df['goal'].isin(VALID_GOALS))
        self._check('D5','campaign_name is not null',mask=self.df['campaign_name'].notna())
        return self.summary()
class CampaignValidator(BaseValidator):
    def __init__(self, df, engine=None, valid_campaign_ids=None):
        super().__init__(df, 'fact_marketing_perf', engine)
        self.valid_campaign_ids=set(valid_campaign_ids) if valid_campaign_ids else set()
    def validate(self):
        self._check('M1','campaign_id is not null',mask=self.df['campaign_id'].notna())
        self._check('M2','campaign_id is unique',mask=~self.df['campaign_id'].duplicated(keep=False))
        if self.valid_campaign_ids:
            self._check('M3','campaign_id exists in dim_campaign',mask=self.df['campaign_id'].isin(self.valid_campaign_ids))
        self._check('M4','impressions > 0',mask=self.df['impressions']>0)
        self._check('M5','clicks <= impressions',mask=self.df['clicks']<=self.df['impressions'])
        self._check('M6','conversions <= clicks',mask=self.df['conversions']<=self.df['clicks'])
        self._check('M7','spend > 0',mask=self.df['spend']>0)
        self._check('M8','revenue >= 0',mask=self.df['revenue']>=0)
        return self.summary()
