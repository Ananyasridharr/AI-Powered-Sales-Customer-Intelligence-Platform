import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from base_validator import BaseValidator
class OrderValidator(BaseValidator):
    def __init__(self, df, engine=None, valid_customer_ids=None, valid_product_ids=None):
        super().__init__(df, 'fact_orders', engine)
        self.valid_customer_ids=set(valid_customer_ids) if valid_customer_ids else set()
        self.valid_product_ids=set(valid_product_ids) if valid_product_ids else set()
    def validate(self):
        self._check('O1','order_id is not null',mask=self.df['order_id'].notna())
        self._check('O2','order_id is unique',mask=~self.df['order_id'].duplicated(keep=False))
        self._check('O3','customer_id is not null',mask=self.df['customer_id'].notna())
        if self.valid_customer_ids:
            self._check('O4','customer_id exists in dim_customer',mask=self.df['customer_id'].isin(self.valid_customer_ids))
        if self.valid_product_ids:
            self._check('O5','product_id exists in dim_product',mask=self.df['product_id'].isin(self.valid_product_ids))
        self._check('O6','price > 0',mask=self.df['price']>0)
        self._check('O7','quantity > 0',mask=self.df['quantity']>0)
        dates=pd.to_datetime(self.df['order_date'],errors='coerce')
        self._check('O8','order_date is valid',mask=dates.notna())
        self._check('O9','no duplicate rows',mask=~self.df.duplicated(keep=False))
        return self.summary()
