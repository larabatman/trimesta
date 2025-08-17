# app/ui_components.py

import streamlit as st

def grade_entry_form():
    """
    Affiche un formulaire pour saisir une note, un coefficient et un trimestre.
    Retourne : (grade: float | None, coeff: float | None, trimester: str | None, submitted: bool)

    - Accepte virgule ou point comme séparateur décimal.
    - Arrondit au dixième (0,1).
    - Coefficient par défaut = 1,0 si non saisi.
    - Valide que la note est comprise entre 0 et 6.
    """
    with st.form('grade_entry'):
        grade_input = st.text_input('Saisir une note', key='grade_input', placeholder='ex. 4,5')
        coeff_input = st.text_input('Coefficient (par défaut = 1,0)', key='coeff_input', value='1,0')
        trimester = st.selectbox('Trimestre', ['T1', 'T2', 'T3'], key='trimester_input')
        submit = st.form_submit_button('Ajouter la note')

    if not submit:
        return None, None, None, False

    # Normalisation des entrées
    g_txt = (grade_input or "").strip()
    c_txt = (coeff_input or "").strip()

    # Conversion et validations
    try:
        grade = round(float(g_txt.replace(',', '.')), 1)
    except ValueError:
        st.error("Format de note invalide. Saisissez un nombre (ex. 4,5).")
        return None, None, None, False

    if not (0 <= grade <= 6):
        st.error("La note doit être comprise entre 0 et 6.")
        return None, None, None, False

    if c_txt == "":
        coeff = 1.0
    else:
        try:
            coeff = round(float(c_txt.replace(',', '.')), 1)
        except ValueError:
            st.error("Format de coefficient invalide. Saisissez un nombre (ex. 1,0).")
            return None, None, None, False

    return grade, coeff, trimester, True
