import os
import requests
from datetime import date
from zipfile import ZipFile
from io import BytesIO

CWD = os.path.join(os.path.dirname(__file__))
if CWD.rstrip('/').endswith('modules'):
    CWD = CWD.rstrip('/').rsplit('/', 1)[0]
TMPDIR = os.path.join(CWD, 'tmp')

HEADERS = {'User-Agent': 'metagov'}


def construct_file_url(filepath, repoDict):
    """Given a repository filepath extracted from the below methods, 
    return a (hopefully valid...) URL for the file

    Note: filepath must be from root = repository root, not full local filepath!"""

    baseURL = repoDict['url']
    if repoDict['ref']:
        baseURL = baseURL.split('/tree')[0]
        branch = repoDict['ref']
    else:
        branch = repoDict['defaultBranch']
    fileURL = baseURL + f'/blob/{branch}/' + filepath
    
    return fileURL
        

def get_github_api_info(githubURL):
    """Get relevant info from the URL string itself and from an API request
    
    Returns rpoDict: dictionary containing repository owner, name, ref, ..."""
    
    # Separate original URL into components
    components = githubURL.split('/')
    domainIndex = [i for (i, s) in enumerate(components) if 'github.com' in s][0]
    repoOwner = components[domainIndex+1]
    repoName = components[domainIndex+2]
    if domainIndex+2 != len(components) - 1:
        ref = components[-1]
    else:
        ref = None
    
    # For reference, get the date that the repository was most recently updated
    apiURL = f"https://api.github.com/repos/{repoOwner}/{repoName}"
    r_base = requests.get(apiURL).json()
    defaultBranch = r_base.get('default_branch', '')
    dateUpdated = ''
    if ref:
        # If version/tag specified
        apiURL = apiURL + '/commits/' + ref
        r_ref = requests.get(apiURL).json()
        dateUpdated = r_ref.get('commit', {}).get('committer', {}).get('date', '')
    else:
        # If main/master
        dateUpdated = r_base.get('updated_at')
        defaultBranch = r_base.get('default_branch')    

    # Define metadata
    repoDict = {'owner': repoOwner,
                'name': repoName,
                'default_branch': defaultBranch,
                'ref': ref,
                'updated_at': dateUpdated,
                'url': githubURL,
                'id': f"{repoOwner}_{repoName}" + (f"_{ref}" if ref else f"_{defaultBranch}")
                }
    
    return repoDict


def get_zipball_api_url(repoDict):
    """Given repository information, construct url for zipball
    
    Returns zipball URL, for specific version of repo if specified
    """
    
    # Construct zip URL
    zipURL = f"https://api.github.com/repos/{repoDict['owner']}/{repoDict['name']}/zipball"
    if repoDict['ref']:
        zipURL = zipURL + '/' + repoDict['ref']
    
    return zipURL
    

def download_repo(githubURL, subdir='contracts', ext='.sol'):
    """Download a specific type of file in a specific subdirectory from a GitHub repository zip file
    
    Arguments:
    - githubURL: valid GitHub URL to repository root (main or a specific version)
    - subdir: specific subdirectory (-ies) to extract content from. Can also be ''
    - ext: specific file extension to keep items from. Can also be '' 
    
    Returns:
    - repoDir: path to local directory
    - repoDict: see get_github_api_info
    
    NOTE: for ease of use with current repo structures of interest, subdir 
    matches ANY subdirectory that includes this folder name
    """

    assert 'github.com' in githubURL, "Download a repository from github.com only"
    if ext is None:
        ext = ''    
    
    repoDir = None
    repoDict = {}
    
    try:
        # Get zip file
        repoDict = get_github_api_info(githubURL)
        zipURL = get_zipball_api_url(repoDict)
        
        r = requests.get(zipURL)
        zipFile = ZipFile(BytesIO(r.content))
        
        # Extract just the relevant subdirectory(-ies) from the zip file
        zipItems = zipFile.infolist()
        baseItem = zipItems[0].filename
        itemCount = 0
        if subdir:
            baseItem = baseItem + subdir.strip('/') + '/'
        for zi in zipItems:
            item = zi.filename
            if (f"/{subdir.strip('/')}/" in item) and item.endswith(ext):
                zipFile.extract(item, TMPDIR)
                itemCount += 1
        
        # Rename directory to {owner}_{name}
        oldName = baseItem.split('/')[0]
        newName = repoDict['id']
        repoDir_old = os.path.join(TMPDIR, oldName)
        repoDir = os.path.join(TMPDIR, newName)
        os.rename(repoDir_old, repoDir)
        
        print(f"Extracted {itemCount} items from {githubURL} to {repoDir}")

    except Exception as e: 
        print(e)

    return repoDir, repoDict

    
if __name__ == "__main__":
    # Test with content in this repository
    testURL = 'https://github.com/notchia/metagov'
    subdir = 'data/contracts'
    repoDir, repoDict = download_repo(testURL, subdir=subdir)
    assert os.path.isdir(repoDir), "could not download/unzip file as specified"
    print(f"Successfully downloaded content from {testURL}")
