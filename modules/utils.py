import ast
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer

def get_unique_col_values(df, col):
    """Get alphabetized list of unique values in a column of single- or multi-select options.
    Useful """

    # Convert all values in column to lists
    try:
        df[col] = df[col].apply(ast.literal_eval)
    except:
        df[col] = df[col].apply(lambda s: [x.strip() for x in str(s).split(',')])
    df[col] = df[col].apply(lambda d: d if isinstance(d, list) else [])

    # One-hot encode column of lists
    mlb = MultiLabelBinarizer(sparse_output=True)
    df_onehot = pd.DataFrame.sparse.from_spmatrix(
        mlb.fit_transform(df[col]),
        index=df.index,
        columns=mlb.classes_)

    # Get count for each unique item
    df_sum = pd.DataFrame(df_onehot.sum()).sort_values(0, axis=0, ascending=False).transpose()

    # Print alphabetized list of unique values
    for i, row in df_sum.iterrows():
        for item in sorted(list(row.index), key=lambda s: (s.lower(), s)):
            print(item)

    return sorted(list(row.index)
