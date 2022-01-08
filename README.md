# Metagov data analysis projects

## Demonstrate Airtable API use and conduct preliminary analysis
Preliminary insights into web3 governance using data on Govbase, in [this notebook](https://github.com/notchia/metagov/blob/main/how_to_use_govbase.ipynb)

Tiny wrapper for Airtable Python library [here](https://github.com/notchia/metagov/blob/main/at2df.py)

## Find governance-related parameters in DAO smart contracts
From the contract text, identify parameters and their contexts (description and function for which each is defined), then find parameters which may be related to governance by defining keywords and searching for these within the parameter descriptions.

Quick first attept for the [Gnosis Safe contract](https://github.com/gnosis/safe-contracts/blob/main/contracts/GnosisSafe.sol) in [this notebook](https://github.com/notchia/metagov/blob/main/find_governance_params_GnosisSafe.ipynb)

More thorough and generalized version in progress in [this notebook](https://github.com/notchia/metagov/blob/main/parse_contract_parameters.ipynb)

## Analyze Cryptogov survey results
Preliminary findings on the Cryptopolitical Typology Quiz in [this notebook](https://github.com/notchia/metagov/blob/main/cryptopolitics_survey_analysis.ipynb)
