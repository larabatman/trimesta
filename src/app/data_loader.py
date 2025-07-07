import pandas as pd
from pathlib import Path

def load_students(file_path: str) -> pd.DataFrame:
    '''Load student names from an Excl file'''
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f'Student file not found: {file_path}')
    
    df = pd.read_excel(path)
    if 'First Name' not in df.columns or 'Last Name' not in df.columns:
        raise ValueError("Excel file must contain 'First Name' and 'Last Name' columns.")
    df['Full Name'] = df['First Name'].str.strip() + ' ' + df['Last Name'].str.strip()
    df['ID'] = df.index
    return df

def save_grades(df: pd.DataFrame, file_path:str):
    '''Save the grades to a CSV file.'''
    df.to_csv(file_path, index = False)

def load_grades(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    expected_cols = ["ID", "Full Name", "Grade", "Coefficient", "Trimester"]

    if not path.exists():
        return pd.DataFrame(columns=expected_cols)

    df = pd.read_csv(path)
    for col in expected_cols:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")
    return df[expected_cols]
