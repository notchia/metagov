import os
import re
import argh
import pandas as pd
from airtable import airtable

CWD = os.path.join(os.path.dirname(__file__))
if CWD.rstrip('/').endswith('modules'):
    CWD = CWD.rstrip('/').rsplit('/', 1)[0]
TMPDIR = os.path.join(CWD, 'tmp')


# Set Airtable access parameters for Govbase
BASE_ID = 'appx3e9Przn9iprkU'
with open('api_key.txt', 'r') as f:
    API_KEY = f.readline().strip()
    

def get_airtable():
    return airtable.Airtable(BASE_ID, API_KEY)


def get_table_as_df(at, tableName):
    """Get all records in a table and load into DataFrame"""
    
    # Get all records
    records = []
    for r in at.iterate(tableName):
        records.append({'id': r['id'], **(r['fields'])})
        
    # Convert to DataFrame
    df = pd.DataFrame(records)
    df.set_index('id', inplace=True)
    
    return df


def push_df_to_table(at, tableName, df, kwargs=None):
    """Get records from DataFrame (directly or as csv) and push to table
    
    TODO: check if a version of the row exists in the table already, and
    if so, handle based on an overwrite/update flag"""

    kwargs_default = {'index_col': 0}
    if kwargs is None:
        kwargs = kwargs_default
    else:
        kwargs = kwargs_default.update(kwargs)      
    
    # If file is supplied, import df from file
    if os.path.isfile(df):
        assert df.endswith('.csv'), "supply a .csv file to which a DataFrame has been saved"
        df = pd.read_csv(df, **kwargs)

    assert isinstance(df, pd.DataFrame), "supply a DataFrame or .csv file to which one was saved"

    # For Airtable compatibility
    df = df.fillna('').astype(str)
    
    # Push each row to the Airtable
    for i, row in df.iterrows():
        try:
            at.create(tableName, row.to_dict())
        except Exception as e:
            print(f"Could not add row {i}: {e}")

def push_dfs_to_table(at, tableName, dirpath, kwargs=None):
    
    fullpath = os.path.join(CWD, dirpath)
    
    assert os.path.isdir(fullpath), "supply a directory path relative to project root"
    
    files = os.listdir(fullpath)
    files.sort()
        
    for f in files:
        print(f"Uploading data from {f}...")
        push_df_to_table(at, tableName, os.path.join(dirpath, f), kwargs=kwargs)


def main(tablename, path):
    at = get_airtable()
    if os.path.isdir(path):
        push_dfs_to_table(at, tablename, path)
    elif os.path.isfile(path):
        push_df_to_table(at, tablename, path)
    else:
        print("provide a valid file or directory")
            
            
if __name__ == "__main__":
    argh.dispatch_command(main)