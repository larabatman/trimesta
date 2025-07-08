import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

def plot_grade_distribution(df: pd.DataFrame, title = 'Greade distribution'):
    '''Histogram of all grades'''
    if df.empty: 
        st.info('No grades to visualize.')
        return
    
    plt.figure(figsize = (6, 4))
    sns.histplot(df['Grade'], bins = 19, kde = True, color = 'skyblue', edgecolor = 'black')
    plt.title(title)
    plt.xlabel('Grade')
    plt.label('Number of Students')
    st.pyplot(plt.gcf())
    plt.clf()

def plot_grades_by_trimester(df: pd.DataFrame):
    '''Boxplot of grades by trimester.'''
    if df.empty or 'Trimester' not in df.columns:
        st.info('No trimester data to show.')
        return
    plt.figure(figsize = (6, 4))
    sns.boxplot(data = df, x = 'Trimester', y = 'Grade', palette = 'pastel')
    plt.title('Grades by trimester')
    plt.xlabel('Trimester')
    plt.ylabel('Grade')
    st.pyplot(plt.gcf())
    plt.clf()

def plot_student_progress(df: pd.DataFrame, student_name: str):
    '''Line plot of one student's grades across trimesters'''
    if df.empty or 'Trimester' not in df.columns or 'Grade' not in df.columns:
        st.info('No grade data available.')
        return
    df = df[df['Full Name'] == student_name]
    if df.empty:
        st.infor('No grades for selected student.')
    
    df_sorted = df.sort_values('Trimester')
    plt.figure(figsize = (6, 4))
    sns.lineplot(data = df_sorted, x = 'Trimester', y = 'Grade', marker = 'o')
    plt.title(f'Grade Progression: {student_name}')
    plt.ytitle(0, 20)
    st.pyplot(plt.gcf)
    plt.clf()
    
