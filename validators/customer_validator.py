import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from base_validator import BaseValidator
VALID_SEGMENTS  = {'Standard', 'Basic', 'Premium', 'Enterprise', 'Trial'}
MIN_SIGNUP_DATE = pd.Timestamp('2010-01-01')
MAX_SIGNUP_DATE = pd.Timestamp('today')
class CustomerValidator(BaseValidator):
    def __init__(self, df, engine=None):
        super().__init__(df, 'dim_customer', engine)
    def validate(self):
        self._check('C1', 'customer_id is not null', mask=self.df['customer_id'].notna())
        self._check('C2', 'customer_id is unique', mask=~self.df['customer_id'].duplicated(keep=False))
        self._check('C3', 'name is not null', mask=self.df['name'].notna())
        self._check('C4', 'city is not null', mask=self.df['city'].notna())
        dates = pd.to_datetime(self.df['signup_date'], errors='coerce')
        self._check('C5', 'signup_date is valid', mask=dates.notna())
        self._check('C6', 'segment is known', mask=self.df['segment'].isin(VALID_SEGMENTS))
        return self.summary()
