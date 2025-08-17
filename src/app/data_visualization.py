import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# --- Utilitaires de normalisation --------------------------------------

def _name_col(df: pd.DataFrame) -> str:
    """Retourne le nom de la colonne 'nom complet' (FR/EN)."""
    for c in ["Full Name", "Nom complet", "Nom Complet", "Nom"]:
        if c in df.columns:
            return c
    return "Full Name"

def _normalize_meta(meta_df: pd.DataFrame) -> pd.DataFrame:
    """Normalise les colonnes du méta-dataframe des évaluations (FR/EN)."""
    if meta_df is None or meta_df.empty:
        return pd.DataFrame(columns=["Assignment", "Coefficient", "Trimester"])

    lower_map = {c.strip().lower(): c for c in meta_df.columns}
    mapping = {}

    def pick(names, target):
        for n in names:
            if n.lower() in lower_map:
                mapping[lower_map[n.lower()]] = target
                return

    pick(["Assignment", "Évaluation", "Evaluation"], "Assignment")
    pick(["Coefficient", "Pondération", "Ponderation"], "Coefficient")
    pick(["Trimester", "Trimestre"], "Trimester")

    meta = meta_df.rename(columns=mapping).copy()
    for col in ["Assignment", "Coefficient", "Trimester"]:
        if col not in meta.columns:
            meta[col] = pd.Series(dtype="object")
    return meta[["Assignment", "Coefficient", "Trimester"]]


# --- Visualisations -----------------------------------------------------

def plot_class_trimester_summary(grade_matrix: pd.DataFrame, meta_df: pd.DataFrame):
    """
    Affiche la moyenne de la classe par évaluation et par trimestre.
    Inclus uniquement les évaluations présentes dans la matrice ET le méta.
    """
    if grade_matrix is None or grade_matrix.empty:
        st.info("Aucune donnée de notes disponible.")
        return

    name_col = _name_col(grade_matrix)
    meta = _normalize_meta(meta_df)
    meta = meta[meta["Assignment"].isin([c for c in grade_matrix.columns if c != name_col])]

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = {"T1": "#8ecae6", "T2": "#ffb703", "T3": "#90be6d"}

    plotted_any = False
    for trimester in ["T1", "T2", "T3"]:
        trimester_assignments = meta[meta["Trimester"] == trimester]["Assignment"]
        if not trimester_assignments.empty:
            # Moyennes par évaluation pour ce trimestre
            means = pd.to_numeric(
                grade_matrix[trimester_assignments], errors="coerce"
            ).mean(skipna=True)

            ax.plot(
                means.index,
                means.values,
                marker="o",
                label=f"Moyenne {trimester}",
                color=colors.get(trimester, None),
                linewidth=2,
            )
            plotted_any = True

    if not plotted_any:
        st.info("Aucune évaluation associée à un trimestre n’est disponible pour la synthèse.")
        return

    ax.set_title("Moyenne de la classe par évaluation et par trimestre")
    ax.set_ylabel("Note")
    ax.set_ylim(0, 6.5)
    ax.grid(True, linestyle="--", alpha=0.5)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax.legend(title="Trimestre")
    st.pyplot(fig)


def plot_grade_distribution(grade_matrix: pd.DataFrame, title="Répartition des notes"):
    """
    Histogramme de toutes les notes (toutes évaluations confondues).
    """
    if grade_matrix is None or grade_matrix.empty:
        st.info("Aucune donnée de notes disponible.")
        return

    name_col = _name_col(grade_matrix)
    # Fondre toutes les colonnes d’évaluations
    melted = (
        grade_matrix.drop(columns=[name_col], errors="ignore")
        .melt(value_name="Note")
        .dropna(subset=["Note"])
    )

    # Conversion sûre en numérique
    melted["Note"] = pd.to_numeric(melted["Note"], errors="coerce")
    melted = melted.dropna(subset=["Note"])

    if melted.empty:
        st.info("Aucune note valide à afficher.")
        return

    fig, ax = plt.subplots(figsize=(7, 4))
    sns.histplot(melted["Note"], bins=12, binrange=(0, 6), kde=True, ax=ax)
    ax.set_title(title)
    ax.set_xlabel("Note")
    ax.set_xlim(0, 6)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    st.pyplot(fig)


def plot_grades_by_assignment(grade_matrix: pd.DataFrame):
    """
    Boxplot des notes par évaluation, avec points individuels en surimpression.
    """
    if grade_matrix is None or grade_matrix.empty:
        st.info("Aucune donnée de notes disponible.")
        return

    name_col = _name_col(grade_matrix)
    melted = (
        grade_matrix.drop(columns=[name_col], errors="ignore")
        .melt(var_name="Évaluation", value_name="Note")
        .dropna(subset=["Note"])
    )

    melted["Note"] = pd.to_numeric(melted["Note"], errors="coerce")
    melted = melted.dropna(subset=["Note"])

    if melted.empty:
        st.info("Aucune note valide à afficher.")
        return

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.boxplot(x="Évaluation", y="Note", data=melted, ax=ax, palette="pastel")
    sns.stripplot(x="Évaluation", y="Note", data=melted, ax=ax, color="black", alpha=0.6, jitter=True)
    ax.set_title("Répartition des notes par évaluation")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax.set_ylim(0, 6.5)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    st.pyplot(fig)


def plot_student_progress(grade_matrix: pd.DataFrame, student_name: str):
    """
    Courbe d’évolution des notes pour un élève.
    """
    if grade_matrix is None or grade_matrix.empty:
        st.info("Aucune donnée de notes disponible.")
        return

    name_col = _name_col(grade_matrix)
    if name_col not in grade_matrix.columns:
        st.warning("Colonne du nom d’élève introuvable.")
        return

    row = grade_matrix[grade_matrix[name_col] == student_name]
    if row.empty:
        st.warning("Élève introuvable.")
        return

    # Série des notes (index = évaluations)
    series = (
        row.drop(columns=[name_col])
        .T.squeeze()
    )

    # Conversion en numérique et suppression des NA
    series = pd.to_numeric(series, errors="coerce").dropna()

    if series.empty:
        st.info("Aucune note disponible pour cet élève.")
        return

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(series.index, series.values, marker="o")
    ax.set_title(f"Évolution de {student_name}")
    ax.set_ylabel("Note")
    ax.set_xlabel("Évaluation")
    ax.set_ylim(0, 6.5)
    ax.grid(True, linestyle="--", alpha=0.5)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    st.pyplot(fig)
