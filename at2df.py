import pandas as pd
from airtable import airtable

# Set Airtable access parameters for Govbase
BASE_ID = 'appx3e9Przn9iprkU'
with open('api_key.txt', 'r') as f:
    API_KEY = f.readline().strip()
    

def get_airtable():
	return airtable.Airtable(BASE_ID, API_KEY)


def get_table_as_df(at, tableName, fields=None):
    """Get all records in a table and load into DataFrame"""
    
    # Get all records
    records = []
    for r in at.iterate(tableName):
        records.append({'id': r['id'], **(r['fields'])})
        
    # Convert to DataFrame
    df = pd.DataFrame(records)
    df.set_index('id', inplace=True)
    
    # Keep only specified fields
    if (fields is not None):
    	assert isinstance(fields, list), "specify a list of fields to keep"
    	df = df[fields]
    
    return df
