import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from base_validator import BaseValidator
VALID_CATEGORIES = {'Electronics','Home & Garden','Clothing','Books','Sports','Beauty'}
class ProductValidator(BaseValidator):
    def __init__(self, df, engine=None):
        super().__init__(df, 'dim_product', engine)
    def validate(self):
        self._check('P1','product_id is not null',mask=self.df['product_id'].notna())
        self._check('P2','product_id is unique',mask=~self.df['product_id'].duplicated(keep=False))
        self._check('P3','product_name is not null',mask=self.df['product_name'].notna())
        self._check('P4','category is known',mask=self.df['category'].isin(VALID_CATEGORIES))
        self._check('P5','brand is not null',mask=self.df['brand'].notna())
        self._check('P6','price_min > 0',mask=self.df['price_min']>0)
        self._check('P7','price_max > price_min',mask=self.df['price_max']>self.df['price_min'])
        self._check('P8','supplier is not null',mask=self.df['supplier'].notna())
        return self.summary()
