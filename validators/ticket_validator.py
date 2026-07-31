import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from base_validator import BaseValidator
VALID_ISSUE_TYPES={'Delayed Delivery','Order Cancellation','Product Defect','Account Access','Payment Issue'}
VALID_STATUSES={'Resolved','Escalated','Pending','Refunded','Closed'}
VALID_CHANNELS={'Phone','Email','Chat','Social Media'}
class TicketValidator(BaseValidator):
    def __init__(self, df, engine=None, valid_customer_ids=None, valid_agent_ids=None):
        super().__init__(df, 'fact_support_tickets', engine)
        self.valid_customer_ids=set(valid_customer_ids) if valid_customer_ids else set()
        self.valid_agent_ids=set(valid_agent_ids) if valid_agent_ids else set()
    def validate(self):
        self._check('T1','ticket_id is not null',mask=self.df['ticket_id'].notna())
        self._check('T2','ticket_id is unique',mask=~self.df['ticket_id'].duplicated(keep=False))
        self._check('T3','customer_id is not null',mask=self.df['customer_id'].notna())
        if self.valid_customer_ids:
            self._check('T4','customer_id exists in dim_customer',mask=self.df['customer_id'].isin(self.valid_customer_ids))
        self._check('T5','issue_type is known',mask=self.df['issue_type'].isin(VALID_ISSUE_TYPES))
        dates=pd.to_datetime(self.df['created_at'],errors='coerce')
        self._check('T6','created_at is valid',mask=dates.notna())
        self._check('T7','resolution_hours > 0',mask=self.df['resolution_hours']>0)
        self._check('T8','satisfaction_score between 1 and 5',mask=(self.df['satisfaction_score']>=1.0)&(self.df['satisfaction_score']<=5.0))
        self._check('T9','agent_id is not null',mask=self.df['agent_id'].notna())
        if self.valid_agent_ids:
            self._check('T10','agent_id exists in dim_support_agent',mask=self.df['agent_id'].isin(self.valid_agent_ids))
        self._check('T11','channel is known',mask=self.df['channel'].isin(VALID_CHANNELS))
        self._check('T12','resolution_status is known',mask=self.df['resolution_status'].isin(VALID_STATUSES))
        return self.summary()
