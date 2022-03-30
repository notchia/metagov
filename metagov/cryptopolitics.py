import os
import pandas as pd
import seaborn as sns

from metagov import at2df # Small custom wrapper functions for the Airtable library
from metagov.utils import ast_eval


def _rename_col(x):
    """Rename question columns to Q{num} to correspond with QUESTIONS keys;
    leave the rest as is"""
    if x[0].isdigit():
        return 'Q'+x.split('.')[0]
    else:
        return x


def q2n(q):
    """Convert column name for question to question number"""
    return int(q[1:])


def n2q(n):
    """Convert question number to column name for question"""
    return f'Q{n}'


def columns_where_rows_differ(df):
    """Get a list of the columns for which the row values differ."""
    return df.nunique(axis=0).where(lambda x: x>1, axis=0).dropna().index.tolist()


# Define list of questions and relevant columns lists, in order
QUESTIONS = {
    'Q1': "1. Which statement comes closest to your views?", 
    'Q2': "2. Which blockchain is the best?", 
    'Q3': "3. Which statement comes closest to your views?", 
    'Q4': "4. Which statement comes closest to your views?", 
    'Q5': "5. Which statement comes closest to your views?", 
    'Q6': "6. Which statement comes closest to your views?", 
    'Q7': "7. Which statement comes closest to your views?", 
    'Q8': "8. Which statement comes closest to your views?", 
    'Q9': "9. In order to grow, the crypto ecosystem should:", 
    'Q10': "10. Which statement comes closest to your views?", 
    'Q11': "11. Which statement comes closest to your views?", 
    'Q12': "12. Which statement comes closest to your views?", 
    'Q13': "13. Which statement comes closest to your views?", 
    'Q14': "14. To get more favorable regulation of cryptocurrencies from national governments, the most important thing the crypto community can do is:", 
    'Q15': "15. Which statement comes closest to your views?", 
    'Q16': "16. Who should have decision-making power over a blockchain?",
    'Q17': "17. I'm here for...", 
    'Q18': "18. Do you consider yourself:", 
    'Q19': "19. OPTIONAL: Do you affiliate with any of the following ecosystems or communities?"
}

CHOICES = {} # Load from dataset

COLS_QUESTIONS = list(QUESTIONS.keys())
COLS_RESULTS = ['classification', 'politics', 'economics', 'governance']

# Define the canonical order for the factions/classes (for display purposes)
FACTION_ORDERS = {
    'politics': ['Crypto-leftist', 'DAOist', 'True neutral', 'Crypto-libertarian', 'Crypto-ancap'],
    'economics': ['Earner', 'Cryptopunk', 'NPC', 'Techtrepreneur', 'Degen'],
    'governance': ['Walchian', 'Zamfirist', 'Noob', 'Gavinist', 'Szabian']
}


def load_data(overwrite=False):
    """Load the data from Govbase. Assumes Govbase data is already clean."""
    
    datapath = 'tmp/cryptopolitics_data.csv'
    if  (not os.path.isfile(datapath)) or overwrite:
        at = at2df.get_airtable()
        df = at2df.get_table_as_df(at, 'Cryptopolitical Typology Quiz')

        # Rename question columns for easier accessing/visualization throughout
        df.rename(columns=_rename_col, inplace=True)
        df.to_csv(datapath)

    else:
        df = pd.read_csv(datapath, index_col=0)
        df['Q19'] = df['Q19'].apply(ast_eval)

    # Split data into question responses and faction results DataFrames
    df_questions = df[COLS_QUESTIONS]
    df_results = df[COLS_RESULTS]

    # Get unique answer choices for each question
    for question in COLS_QUESTIONS[:-1]:
        choices = list(df_questions[question].unique())
        CHOICES[question] = choices

    return {'responses': df_questions, 'results': df_results}


# Plot formatting
DEFAULT_COLOR = '#66C2A5'
sns.set(rc={"figure.figsize":(7, 5)})
sns.set(font_scale=1.25)

# Output settings
SAVE = True
SAVEDIR = os.path.join(os.getcwd(), 'tmp')
KWARGS_SVG = {'format': 'svg', 'bbox_inches': 'tight'}
KWARGS_PNG = {'format': 'png', 'bbox_inches': 'tight', 'dpi': 600}


if __name__ == "__main__":
    from datetime import datetime

    # Test database loading
    t0 = datetime.now()
    load_data(overwrite=True)
    t1 = datetime.now()
    print(f"Time to load from Airtable: {t1-t0}")
    load_data()
    t2 = datetime.now()
    print(f"Time to load from file:     {t2-t1}")