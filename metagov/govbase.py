import os
import numpy as np
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer

from metagov import at2df
from metagov.utils import ast_eval


def load_data_from_contract_tables(overwrite=False):
    """Load Contract Objects and Contract Parameters "Keyword-coded records views from Govbase"
    (or, locally from file if it exists)"""
    
    datapath_objects = 'tmp/airtable_contract_objects_data.csv'
    datapath_params = 'tmp/airtable_contract_parameters_data.csv'
    
    if overwrite or not (os.path.isfile(datapath_objects) and os.path.isfile(datapath_params)):
        # Load from Airtable
        at = at2df.get_airtable()
        kwargs = {'view': 'Keyword-coded records'}
        df_objects = at2df.get_table_as_df(at, 'Contract Objects', kwargs=kwargs)
        df_params = at2df.get_table_as_df(at, 'Contract Parameters', kwargs=kwargs)
        
        # Drop unnecessary colums 
        df_objects.drop(columns=['notice', 'full_comment', 'param', 'return', 'dev', 'title',
                                 'coding_keyword_search', 'coding_topic_search',
                                 'coding_keyword_search_options', 'coding_topic_search_options',
                                 'url', 'repo_url', 'repo_update_datetime', 'repo_version'
                                ], 
                        inplace=True, errors='ignore')
        df_params.drop(columns=['full_comment', 'coding_keyword_search_options_from_object', 
                                'project_from_object', 'type_from_object', 'visibility_from_object',
                                'url'], 
                       inplace=True, errors='ignore')
        
        # Load list columns (and convert always-single-item list to string)
        for col in ['inheritance', 'modifiers', 'values']:
            df_objects[col] = df_objects[col].apply(ast_eval)
        df_params['object_id'] = df_params['object_id'].apply(lambda x: x[0] if isinstance(x, list) else x)
        
        # Save to local file
        df_objects.to_csv(datapath_objects)
        df_params.to_csv(datapath_params)

    else:
        # Load from local file
        df_objects = pd.read_csv(datapath_objects, index_col=0)
        df_params = pd.read_csv(datapath_params, index_col=0)
        
        # Load list columns
        for col in ['contract_parameters', 'hand_coding', 'inheritance', 'modifiers', 'values']:
            df_objects[col] = df_objects[col].apply(ast_eval)
        for col in ['hand_coding_from_object']:
            df_params[col] = df_params[col].apply(ast_eval)

    # Load child parameter names into df_objects for ease of analysis
    df_objects['contract_parameters_names'] = df_objects['contract_parameters'].apply(
        lambda values: [df_params.at[v, 'parameter_name'] for v in values] if isinstance(values, list) else np.nan
    )

    # Note that this assumes that the parent object of each parameter has been tagged with the same keyword;
    # This is enforced in the automated version, but could possibly have been broken in the hand-coding, so watch out for this
    df_params['project'] = df_params['object_id'].apply(lambda v: df_objects.at[v,'project'])

    # One-hot encode keywords for each
    mlb = MultiLabelBinarizer(sparse_output=True)
    df_objects_kws = pd.DataFrame.sparse.from_spmatrix(
        mlb.fit_transform(df_objects['hand_coding']),
        index=df_objects.index,
        columns=mlb.classes_)
    df_objects = df_objects.join(df_objects_kws)

    return {'objects': df_objects, 'parameters': df_params}