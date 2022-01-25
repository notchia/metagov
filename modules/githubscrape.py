import os
import requests
from datetime import date
from zipfile import ZipFile
from io import BytesIO

CWD = os.path.join(os.path.dirname(__file__))
if CWD.rstrip('/').endswith('modules'):
    CWD = CWD.rstrip('/').rsplit('/', 1)[0]
TMPDIR = os.path.join(CWD, 'tmp')


def get_zipball_api_url(githubURL):
    """Given repository URL, construct url for zipball
    githubURL may be for a specific version, not necessarily main
    
    Returns:
    - zipURL: zipball URL, for specific version of repo if specified
    - repoDict: dictionary containing repository owner, name, and ref
    """
    
    # Separate original URL into components
    components = githubURL.split('/')
    domainIndex = [i for (i, s) in enumerate(components) if 'github.com' in s][0]
    repoOwner = components[domainIndex+1]
    repoName = components[domainIndex+2]
    if domainIndex+2 != len(components) - 1:
        ref = components[-1]
    else:
        ref = None
    
    # Construct zip URL
    zipURL = f"https://api.github.com/repos/{repoOwner}/{repoName}/zipball"
    if ref:
        zipURL = zipURL + '/' + ref
    
    repoDict = {'owner': repoOwner,
                'name': repoName,
                'ref': ref,
                'date_accessed': date.today().strftime("%Y-%m-%d")}
    
    return zipURL, repoDict
    

def download_repo(githubURL, subdir='contracts', ext='.sol'):
    """Download a specific type of file in a specific subdirectory from a GitHub repository zip file
    
    Arguments:
    - githubURL: valid GitHub URL to repository root (main or a specific version)
    - subdir: specific subdirectory to extract content from. Can also be '' or None
    - ext: specific file extension to keep items from. Can also be '' 
    
    NOTE: for ease of use with current repo structures of interest, subdir now
    matches ANY subdirectory that includes this folder name
    """

    assert 'github.com' in githubURL, "Download from github.com only"
    if ext is None:
        ext = ''    
    
    repoDir = None
    repoDict = {}
    
    try:
        # Get zip file
        zipURL, repoDict = get_zipball_api_url(githubURL)
        print(zipURL)
        r = requests.get(zipURL)
        zipFile = ZipFile(BytesIO(r.content))
        
        # Extract just the relevant subdir from the zip file
        zipItems = zipFile.infolist()
        baseItem = zipItems[0].filename
        if subdir:
            baseItem = baseItem + subdir.strip('/') + '/'
        for zi in zipItems:
            item = zi.filename
            if (f"/{subdir.strip('/')}/" in item) and item.endswith(ext):
                print(f"extracting {item}...")
                zipFile.extract(item, TMPDIR)
            
        
        # Rename directory to {owner}_{name}
        oldName = baseItem.split('/')[0]
        newName = repoDict['owner'] + '_' + repoDict['name']
        repoDir_old = os.path.join(TMPDIR, oldName)
        repoDir = os.path.join(TMPDIR, newName)
        os.rename(repoDir_old, repoDir)

    except Exception as e: 
        print(e)
        
    print(repoDir)

    return repoDir, repoDict

    
if __name__ == "__main__":
    testURL = 'https://github.com/notchia/metagov'
    subdir = 'data/contracts'
    clean = False
    
    repoDir, repoDict = download_repo(testURL, subdir=subdir)
    assert os.path.isdir(repoDir), "could not download/unzip file as specified"
