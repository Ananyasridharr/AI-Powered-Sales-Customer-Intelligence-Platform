import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from sqlalchemy import create_engine
from customer_validator import CustomerValidator
from product_validator import ProductValidator
from order_validator import OrderValidator
from campaign_validator import CampaignValidator, CampaignDimValidator
from session_validator import SessionValidator
from ticket_validator import TicketValidator
DB_USER='postgres'
DB_PASSWORD='idontknow2005'
DB_HOST='localhost'
DB_PORT='5432'
DB_NAME='AI-Powered Sales & Customer Intelligence Platform'
SCHEMA='warehouse'
engine=create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
print('\n'+'='*65+'\n  NEXUSIQ — FULL DATA VALIDATION SUITE\n'+'='*65)
with engine.connect() as conn:
    dim_customer=pd.read_sql(f'SELECT * FROM {SCHEMA}.dim_customer',conn)
    dim_product=pd.read_sql(f'SELECT * FROM {SCHEMA}.dim_product',conn)
    dim_campaign=pd.read_sql(f'SELECT * FROM {SCHEMA}.dim_campaign',conn)
    dim_agent=pd.read_sql(f'SELECT * FROM {SCHEMA}.dim_support_agent',conn)
    fact_orders=pd.read_sql(f'SELECT * FROM {SCHEMA}.fact_orders',conn)
    fact_activity=pd.read_sql(f'SELECT * FROM {SCHEMA}.fact_customer_activity',conn)
    fact_tickets=pd.read_sql(f'SELECT * FROM {SCHEMA}.fact_support_tickets',conn)
    fact_marketing=pd.read_sql(f'SELECT * FROM {SCHEMA}.fact_marketing_perf',conn)
customer_ids=dim_customer['customer_id'].tolist()
product_ids=dim_product['product_id'].tolist()
campaign_ids=dim_campaign['campaign_id'].tolist()
agent_ids=dim_agent['agent_id'].tolist()
scoreboard=[]
validators=[
    ('dim_customer',CustomerValidator(dim_customer,engine)),
    ('dim_product',ProductValidator(dim_product,engine)),
    ('dim_campaign',CampaignDimValidator(dim_campaign,engine)),
    ('fact_orders',OrderValidator(fact_orders,engine,customer_ids,product_ids)),
    ('fact_marketing_perf',CampaignValidator(fact_marketing,engine,campaign_ids)),
    ('fact_customer_activity',SessionValidator(fact_activity,engine,customer_ids)),
    ('fact_support_tickets',TicketValidator(fact_tickets,engine,customer_ids,agent_ids)),
]
for table_name,validator in validators:
    result=validator.validate()
    scoreboard.append({'table':table_name,'passed':result['passed'],'failed':result['failed'],'total':result['total']})
print('\n'+'='*65+'\n  FINAL SCORECARD\n'+'='*65)
print(f"  {'Table':<35} {'Rules':>6} {'Pass':>6} {'Fail':>6}  Status")
print('-'*65)
all_ok=True
for s in scoreboard:
    status='[CLEAN]' if s['failed']==0 else ('[WARN]' if s['failed']<=2 else '[FAIL]')
    if s['failed']>0: all_ok=False
    print(f"  {s['table']:<35} {s['total']:>6} {s['passed']:>6} {s['failed']:>6}  {status}")
print('='*65)
print('  ALL CLEAR' if all_ok else '  ISSUES FOUND — review logs above')
print('='*65+'\n')
