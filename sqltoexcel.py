import pandas as pd
from sqlalchemy import create_engine, inspect

# Update with your PostgreSQL credentialspostgresql+psycopg2://postgres:idontknow2005@localhost:5432/AI-Powered Sales & Customer Intelligence Platform
DB_URI = ""
engine = create_engine(DB_URI)
inspector = inspect(engine)

# Fetch all table names from the public schema
table_names = inspector.get_table_names(schema="warehouse")

# Export all tables into a single Excel workbook
with pd.ExcelWriter("postgresql_export.xlsx", engine="openpyxl") as writer:
    for table in table_names:
        print(f"Exporting {table}...")
        # Read table data into a dataframe
        df = pd.read_sql_table(table, con=engine, schema="warehouse")
        # Write to a dedicated worksheet tab (Excel tabs are restricted to 31 characters)
        df.to_excel(writer, sheet_name=table[:31], index=False)

print("Export complete! Saved as 'postgresql_export.xlsx'.")
