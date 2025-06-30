import streamlit as st
import pandas as pd
from app.data_loader import load_students

#Load students from Excel file
students_df = load_students('data/901.xlsx')

st.title('Trimesta')

# Input field
search = st.text_input('Search student', placeholder = 'Start typing a name...')

# Display matching students
if search: 
    matches = students_df[students_df['Full Name'].str.lower().str.contains(search.lower())]
    if not matches.empty:
        st.subheader('Matching students:')
        for name in matches['Full Name']:
            st.write(f'{name}')
        else:
            st.warning('No matching student found')
    else: 
        st.info('Start typing a name to seach.')