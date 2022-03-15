# Metagov data analysis projects
As a data scientist at the [Metagovernance Project](https://metagov.org/), I support a variety of projects about **governance in Web3**, investigating what forms it currently takes, what people think about it, and what it could look like in the future. This repository contains Jupyter notebooks for some of these projets, as well as supporting data, additional Python modules for use in these notebooks, and some results of this work.

## If you want to run this repository yourself...
Make sure to create a Python environment from `requirements.txt`. If you are using Anaconda, you'll need to run the following commands:
```
conda create -n metagov python=3.9
conda activate metagov
pip install -r requirements.txt
```

## Dive into the Govbase projects, organizations, and structures tables
Gain some insight into current projects and organizations involved in Web3 governance using data on [Govbase](https://airtable.com/shrgnUrj0dqzZDsOd/tblvk3EFzcoCFvXXi/viwTisATNcua7os4y), Metagov's big public Airtable database. Learn more about Govbase in [this Medium article](https://medium.com/metagov/introducing-govbase-97884b0ddaef).

- Analysis notebook: [how_to_use_govbase.ipynb](https://github.com/notchia/metagov/blob/main/how_to_use_govbase.ipynb)
- Tiny wrapper for Airtable Python library to get/set data as pandas DataFrames: [modules/at2df.py](https://github.com/notchia/metagov/blob/main/at2df.py)

## Find governance-related parameters in DAO smart contracts
From the contract text, identify parameters and their contexts (description and function for which each is defined), then find parameters which may be related to governance by defining keywords and searching for these within the parameter descriptions.

- Quick first attempt for the Gnosis Safe contract: [find_governance_params_GnosisSafe.ipynb](https://github.com/notchia/metagov/blob/main/find_governance_params_GnosisSafe.ipynb)
- More thorough and generalized version in progress: [parse_contract_parameters.ipynb](https://github.com/notchia/metagov/blob/main/parse_contract_parameters.ipynb)

## Analyze political, economic, and governance beliefs across crypto communities
The [Cryptopolitical Typology Quiz](https://metagov.typeform.com/cryptopolitics) was developed by Metagov to help the crypto community understand its political, economic, and governance beliefs. Live survey results are available in a [Typeform report](https://metagov.typeform.com/report/bz9SbjUU/ZY07qRfTs68oypzt).

- Preliminary findings from data available as of January 9, 2022 on the Govbase Airtable database: [cryptopolitics_survey_analysis.ipynb](https://github.com/notchia/metagov/blob/main/cryptopolitics_survey_analysis.ipynb)
- Figures for article in [results](https://github.com/notchia/metagov/tree/main/results) folder; ordinal encoding used for clustering/feature selection (where possible) in [cryptopolitics_quiz_cluster_mapping.csv](https://github.com/notchia/metagov/blob/main/data/cryptopolitics_quiz_cluster_mapping.csv)
