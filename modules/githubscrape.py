import os
import re
import requests
from zipfile import ZipFile
from io import BytesIO

CWD = os.path.join(os.path.dirname(__file__), '..')
TMPDIR = os.path.join(CWD, 'tmp')

EXCLUDE_DIRS = ['lib', 'test']
EXCLUDE_FILES = ['SafeMath.sol', 'lib.sol']
EXCLUDE_FILE_PATTERNS = [r'I?ERC\d+.sol', r'I?EIP\d+.sol']


def download_repo(githubURL, subfolder='contracts'):
	"""Download a specific subfolder's content from GitHub repository zip file"""
	
	assert 'github.com' in githubURL, "Download from github.com only"
	
	contractsFolder = None
	
	try:
		# Set zip file URL
		repoOwner, repoName = githubURL.strip('/').split('/')[-2:]
		zipURL = f"https://api.github.com/repos/{repoOwner}/{repoName}/zipball"	
	
		# Get zip file
		r = requests.get(zipURL)
		d = r.headers['content-disposition']
		fname = os.path.splitext(re.findall("filename=(.+)", d)[0])[0]
		zipItem = f"{fname}/{subfolder.strip('/')}/"
		
		# Extract just the relevant subfolder from the zip file
		zipFile = ZipFile(BytesIO(r.content))
		for zi in zipFile.infolist():
			item = zi.filename
			if item.startswith(zipItem):
				zipFile.extract(zi.filename, TMPDIR)
		
		contractsFolder = os.path.join(TMPDIR, zipItem)
		print(contractsFolder)
		
	except Exception as e: 
		print(e)
		
	return contractsFolder


def walk_through_contracts(contractsDir, excludeFiles=[], includeFiles=[], excludeDirs=[], includeDirs=[], useDefaults=True):
	"""Walk through contracts and apply some function to the relevant files"""
	
	assert os.path.isdir(contractsDir), "specify an existing directory"
	assert not (len(excludeFiles) > 0 and len(includeFiles) > 0), "specify only files to exclude or to include, not both"
	assert not (len(excludeDirs) > 0 and len(includeDirs) > 0), "specify only subfolder names to exclude or to include, not both"
	
	if useDefaults:
		excludeFiles += EXCLUDE_FILES
		excludeDirs += EXCLUDE_DIRS
		
	for root, dirnames, filenames in os.walk(contractsDir, topdown=True):
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
		
		# Apply the function
		for fname in filenames:
			fpath = os.path.join(root, fname)
			print(fpath)
		

if __name__ == "__main__":
	testURL = 'https://github.com/notchia/metagov'
	contractsFolder = download_repo(testURL, subfolder='data/contracts')
	if contractsFolder:
		walk_through_contracts(contractsFolder)
		
	
