import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from base_validator import BaseValidator
VALID_DEVICES={'Mobile','Desktop','Tablet'}
class SessionValidator(BaseValidator):
    def __init__(self, df, engine=None, valid_customer_ids=None):
        super().__init__(df, 'fact_customer_activity', engine)
        self.valid_customer_ids=set(valid_customer_ids) if valid_customer_ids else set()
    def validate(self):
        self._check('S1','session_id is not null',mask=self.df['session_id'].notna())
        self._check('S2','session_id is unique',mask=~self.df['session_id'].duplicated(keep=False))
        self._check('S3','customer_id is not null',mask=self.df['customer_id'].notna())
        if self.valid_customer_ids:
            self._check('S4','customer_id exists in dim_customer',mask=self.df['customer_id'].isin(self.valid_customer_ids))
        ts=pd.to_datetime(self.df['activity_timestamp'],errors='coerce')
        self._check('S5','activity_timestamp is valid',mask=ts.notna())
        self._check('S6','session_duration_sec > 0',mask=self.df['session_duration_sec']>0)
        self._check('S7','device_type is known',mask=self.df['device_type'].isin(VALID_DEVICES))
        pv=self.df['page_view']
        self._check('S8','page_view is true for all',mask=pv if pv.dtype==bool else pv==1)
        pur=self.df['purchase']; chk=self.df['checkout']; atc=self.df['add_to_cart']
        if pur.dtype==bool:
            self._check('S9','purchase implies checkout',mask=~pur|chk)
            self._check('S10','checkout implies add_to_cart',mask=~chk|atc)
        else:
            self._check('S9','purchase implies checkout',mask=(pur==0)|(chk==1))
            self._check('S10','checkout implies add_to_cart',mask=(chk==0)|(atc==1))
        return self.summary()
