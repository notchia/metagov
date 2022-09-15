import os
import re
import argh
import pandas as pd
import ast
from airtable import airtable

from metagov.utils import get_unique_col_values

CWD = os.path.join(os.path.dirname(__file__))
if CWD.rstrip('/').endswith('metagov'):
    CWD = CWD.rstrip('/').rsplit('/', 1)[0]
TMPDIR = os.path.join(CWD, 'tmp')


def get_airtable():
    # Set Airtable access parameters for Govbase
    BASE_ID = 'appx3e9Przn9iprkU'
    with open('api_key.txt', 'r') as f:
        API_KEY = f.readline().strip()
        
    return airtable.Airtable(BASE_ID, API_KEY)


def get_table_as_df(at, tableName, kwargs=None):
    """Get all records in a table and load into DataFrame"""
    
    if kwargs is None:
        kwargs = {}

    # Get all records
    records = []
    for r in at.iterate(tableName, **kwargs):
        records.append({'id': r['id'], **(r['fields'])})
        
    # Convert to DataFrame
    df = pd.DataFrame(records)
    df.set_index('id', inplace=True)
    
    return df


def load_df_from_csv(path, kwargs=None):
    _kwargs = {'index_col': 0}
    if kwargs is not None:
        _kwargs.update(kwargs)

    # If file is supplied, import df from file
    if os.path.isfile(path):
        assert path.endswith('.csv'), "supply a .csv file to which a DataFrame has been saved"
        df = pd.read_csv(path, **_kwargs)

    assert isinstance(df, pd.DataFrame), "supply a DataFrame or .csv file to which one was saved"

    return df


def push_df_to_table(at, tableName, df, kwargs=None):
    """Get records from DataFrame (directly or as csv) and push to table
    
    TODO: check if a version of the row exists in the table already, and
    if so, handle based on an overwrite/update flag"""

    df = load_df_from_csv(df, kwargs=kwargs)

    # For Airtable compatibility
    df = df.fillna('').astype(str)
    
    # Push each row to the Airtable
    for i, row in df.iterrows():
        try:
            at.create(tableName, row.to_dict())
        except Exception as e:
            print(f"Could not add row {i}: {e}")


def push_dfs_to_table(at, tableName, dirpath, kwargs=None):
    """Push directory of .csv files to table"""

    fullpath = os.path.join(CWD, dirpath)
    
    assert os.path.isdir(fullpath), "supply a directory path relative to project root"
    
    files = os.listdir(fullpath)
    files.sort()
        
    for f in files:
        print(f"Uploading data from {f}...")
        push_df_to_table(at, tableName, os.path.join(dirpath, f), kwargs=kwargs)


def debug_column(path, col, kwargs=None):
    """Print list of unique values in column
    May need to manually add options to single- or multi-select columns in Airtable"""

    df = load_df_from_csv(path, kwargs=kwargs)
    get_unique_col_values(df, col)


def main(tablename, path, debug=False, kwargs=None, col=None):
    """Command line interface for pushing .csv file(s) to Airtable"""

    if kwargs is not None:
        _kwargs = ast.literal_eval(kwargs)
    else:
        _kwargs = {}

    if debug:
        assert col is not None, "supply a column name to troubleshoot"
        debug_column(path, col, kwargs=_kwargs)
    else:
        at = get_airtable()
        if os.path.isdir(path):
            push_dfs_to_table(at, tablename, path, kwargs=_kwargs)
        elif os.path.isfile(path):
            push_df_to_table(at, tablename, path, kwargs=_kwargs)
        else:
            print("provide a valid file or directory")
            
            
if __name__ == "__main__":
    argh.dispatch_command(main)