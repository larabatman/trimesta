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

def load_grades(file_path: str) -> pd.DataFrame:
    '''Load grades from a separate file'''
    path = Parh(file_path)
    if not path.exists():
        return pd.DataFrame(columns=['ID', 'Subject', 'Grade', 'Coefficient', 'Trimester'])
    
    return pd.read_csv(path)

def save_grades(df: pd.DataFrame, file_path: str):
    '''Save the grades to a CSV file'''
    df.to_csv(file_path, index = False)
