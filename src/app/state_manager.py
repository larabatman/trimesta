# app/state_manager.py

import streamlit as st
import pandas as pd
from app.data_loader import load_grades

def init_session_state():
    """Initializes the grades table in session state, loading from disk if available."""
    if "grades_df" not in st.session_state:
        df = load_grades("data/grades_901.csv")
        expected_cols = ["ID", "Full Name", "Grade", "Coefficient", "Trimester"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = pd.Series(dtype="object")
        st.session_state["grades_df"] = df[expected_cols]
