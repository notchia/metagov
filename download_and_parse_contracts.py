import os
import re
import ast
import pandas as pd

from modules.githubscrape import download_repo
from modules.contractmodel import parse_contract_file

CWD = os.path.join(os.path.dirname(__file__))
if CWD.rstrip('/').endswith('modules'):
    CWD = CWD.rstrip('/').rsplit('/', 1)[0]
TMPDIR = os.path.join(CWD, 'tmp')

EXCLUDE_DIRS = ['lib', 'test']
EXCLUDE_FILES = ['SafeMath.sol', 'lib.sol']
EXCLUDE_FILE_PATTERNS = [r'I?ERC\d+.sol', r'I?EIP\d+.sol']


def parse_repo(projectDir, projectLabel='', useDefaults=True, 
               excludeFiles=[], includeFiles=[], excludeDirs=[], includeDirs=[]):
    """Walk through contracts and apply some function to the relevant files"""
    
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

    projectFolder = projectDir.strip('/').split('/')[-1]

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
            fileLabel = f"{projectFolder}/{subdir.strip('/')}/{fname.split('.')[0]}"
            try:
                df_o, df_p = parse_contract_file(fpath, label=fileLabel)
                df_objects = df_objects.append(df_o)
                df_parameters = df_parameters.append(df_p)
                fileCount += 1
            except Exception as e:
                print(f"! Error parsing {fname}: {e}")
                errorFiles.append(os.path.join(subdir, fname))
        
    # Save parsed data to files
    df_objects['project'] = projectLabel
    if (len(df_objects.index) > 0):
        df_objects.drop(columns=['line_numbers']).to_csv(os.path.join(TMPDIR, f'contract_objects_{projectLabel}.csv'))
        df_parameters.drop(columns=['line_number']).to_csv(os.path.join(TMPDIR, f'contract_parameters_{projectLabel}.csv'))
    
    print(f"Summary: parsed {fileCount} files")
    print("Could not parse the following files:")
    for f in errorFiles:
        print(f"\t{f}")
    

def main(githubURL, label=''):
    """Download and parse repo"""
    
    repoDir, repoDict = download_repo(githubURL)
    #repoDir = '/home/notchia/Repositories/metagov/tmp/openlawteam_tribute-contracts'
    #repoDict = {'owner': 'openlawteam', 'name': 'tribute-contracts', 'ref': 'v2.3.4'}
    
    assert os.path.isdir(repoDir), "could not download/unzip file as specified"

    if label == '':
        label = f"{repoDict['owner']}_{repoDict['name']}"
    parse_repo(repoDir, projectLabel=label)
    
    
if __name__ == '__main__':
    #main('https://github.com/openlawteam/tribute-contracts/tree/v2.3.4', "OpenLaw_Tribute")
    main('https://github.com/aragon/govern/tree/v1.0.0-beta.12', "Aragon_Aragon-Govern")