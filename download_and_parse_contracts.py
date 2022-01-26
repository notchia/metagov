import os
import re
import ast
import pandas as pd

from modules.githubscrape import download_repo, construct_file_url
from modules.contractmodel import parse_contract_file

CWD = os.path.join(os.path.dirname(__file__))
if CWD.rstrip('/').endswith('modules'):
    CWD = CWD.rstrip('/').rsplit('/', 1)[0]
TMPDIR = os.path.join(CWD, 'tmp')

# The following default values can be added to or overridden
EXCLUDE_DIRS = ['lib', 'libs', 'libraries', 'test', 'tests', 'test-helpers', 'testHelpers', 'example', 'examples', 'migration']
EXCLUDE_FILES = ['SafeMath.sol', 'lib.sol', 'Migrations.sol']
EXCLUDE_FILE_PATTERNS = [r'I?ERC\d+\.sol', r'I?EIP\d+\.sol', r'.*\.t\.sol']


def parse_repo(projectDir, repoDict, projectLabel='', useDefaults=True, clean=False,
               excludeFiles=[], includeFiles=[], excludeDirs=[], includeDirs=[]):
    """Walk through contracts and parsethe relevant files
    
    Explicitly only attempts to parse .sol files"""
    
    assert os.path.isdir(projectDir), "specify an existing directory"
    assert not (len(excludeFiles) > 0 and len(includeFiles) > 0), "specify only files to exclude or to include, not both"
    assert not (len(excludeDirs) > 0 and len(includeDirs) > 0), "specify only subdirectory names to exclude or to include, not both"
    
    if useDefaults:
        excludeFiles += EXCLUDE_FILES
        excludeDirs += EXCLUDE_DIRS

    errorFiles = []
    fileCount = 0

    df_objects = pd.DataFrame()
    df_parameters = pd.DataFrame()

    print(f"Walking through {projectDir}...")
    for root, dirnames, filenames in os.walk(projectDir, topdown=True):
        subdir = root.split(projectDir)[-1]
        print(f"> {subdir}")
        
        # Filter dirnames
        if len(includeDirs) > 0:
            dirnames[:] = [d for d in dirnames if d in includeDirs]
        else:
            dirnames[:] = [d for d in dirnames if d not in excludeDirs]

        # Filter filenames
        if len(includeFiles) > 0:
            filenames = [f for f in filenames if f in includeFiles]
        else:
            filenames = [f for f in filenames if f.endswith('.sol')]
            filenames = [f for f in filenames if f not in excludeFiles]
            if useDefaults:
                filenames = [f for f in filenames if not any([re.match(p, f) for p in EXCLUDE_FILE_PATTERNS])]

        # Parse each file and append objects and parameters to main dfs
        for fname in filenames:
            fpath = os.path.join(root, fname)
            try:
                df_o, df_p = parse_contract_file(fpath, label=repoDict['name'])
                fileURL = construct_file_url(f"{subdir.strip('/')}/{fname}", repoDict)
                df_o['url'] = fileURL
                df_p['url'] = fileURL
                df_objects = df_objects.append(df_o)
                df_parameters = df_parameters.append(df_p)
                fileCount += 1
            except Exception as e:
                print(f"! Error parsing {fname}: {e}")
                errorFiles.append(os.path.join(subdir, fname))
        
    # Save parsed data to files
    if (len(df_objects.index) > 0):
        df_objects['project'] = projectLabel
        df_objects['repo_last_updated'] = repoDict['updated_at']
        df_objects['repo_version'] = repoDict['ref']
        df_objects['repo_url'] = repoDict['url']
        df_objects.drop(columns=['line_numbers']).to_csv(os.path.join(TMPDIR, f'contract_objects_{projectLabel}.csv'))
        df_parameters.drop(columns=['line_number']).to_csv(os.path.join(TMPDIR, f'contract_parameters_{projectLabel}.csv'))
    
    print(f"\nSummary for {projectLabel}: parsed {fileCount} files")
    if len(errorFiles) > 0:
        print("Could not parse the following files:")
        for f in errorFiles:
            print(f"\t{f}")
            
    if clean:
        os.rmdir(projectDir)
            

def load_list(s):
    try:
        l = ast.literal_eval(s)
    except (ValueError, SyntaxError):
        l = s
    return l


def import_contracts(csv):
    df_contracts = pd.read_csv(csv)
    df_contracts.fillna('', inplace=True)
    df_contracts.drop(columns=['url', 'notes'], inplace=True)

    for col in ['excludeDirs', 'includeDirs', 'excludeFiles', 'includeFiles']:
        df_contracts[col] = df_contracts[col].apply(load_list)
    
    return df_contracts


def download_and_parse(githubURL, label='', kwargs={}):
    repoDir, repoDict = download_repo(githubURL)
    
    assert os.path.isdir(repoDir), "could not download/unzip file as specified"

    if label == '':
        label = repoDict['id']
    parse_repo(repoDir, repoDict, projectLabel=label, **kwargs)
    

def main():
    csv = os.path.join(CWD, 'data/repos.csv')
    df_contracts = import_contracts(csv)
    
    for i, row in df_contracts.iterrows():
        kwargs = {c: row[c] for c in ['excludeDirs', 'includeDirs', 'excludeFiles', 'includeFiles'] if row[c]}
        kwargs['clean'] = True
        if 'Colony' in row['project']:
            download_and_parse(row['repoURL'], label=row['project'], kwargs=kwargs)
    
    
if __name__ == '__main__':
    main()
        