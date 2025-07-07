# This module handles calculations on grades_df

import pandas as pd

def compute_weighted_average(df: pd.DataFrame) -> float | None:
    ''' 
    Computes the weighted average of a grades DataFrame.
    Excpects columns: 'Grade', 'Coefficient'.
    Returns None if no valid data.
    '''
    if df.empty or 'Grade' not in df.columns or 'Coefficient' not in df.columns:
        return None
    
    total_weight = df['Coefficient'].sum()
    if total_weight <= 0 :
        return None
    
    weighted_sum = (df['Grade'] * df['Coefficient']).sum()
    return round(weighted_sum / total_weight, 2)