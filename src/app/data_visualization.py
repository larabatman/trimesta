# src/app/data_visualization.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

# -----------------------------
# Utilitaires de normalisation
# -----------------------------
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

    lower_map = {str(c).strip().lower(): c for c in meta_df.columns}
    mapping = {}

    def pick(names, target):
        for n in names:
            key = n.lower()
            if key in lower_map:
                mapping[lower_map[key]] = target
                return

    pick(["Assignment", "Évaluation", "Evaluation"], "Assignment")
    pick(["Coefficient", "Pondération", "Ponderation"], "Coefficient")
    pick(["Trimester", "Trimestre"], "Trimester")

    meta = meta_df.rename(columns=mapping).copy()
    for col in ["Assignment", "Coefficient", "Trimester"]:
        if col not in meta.columns:
            meta[col] = pd.Series(dtype="object")
    return meta[["Assignment", "Coefficient", "Trimester"]]

# -----------------------------
# Visualisations
# -----------------------------

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

    # Ne garder que les évaluations qui existent dans la matrice
    existing_cols = [c for c in grade_matrix.columns if c != name_col]
    meta = meta[meta["Assignment"].isin(existing_cols)].copy()

    if meta.empty:
        st.info("Aucune évaluation associée à un trimestre n’est disponible pour la synthèse.")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = {"T1": "#8ecae6", "T2": "#ffb703", "T3": "#90be6d"}
    plotted_any = False

    for trimester in ["T1", "T2", "T3"]:
        cols = meta.loc[meta["Trimester"] == trimester, "Assignment"].tolist()
        if cols:
            # Sélection + conversion numérique colonne par colonne
            sub = grade_matrix[cols].apply(pd.to_numeric, errors="coerce")
            means = sub.mean(skipna=True)

            # Préserver l’ordre d’origine des colonnes
            means = means.reindex(cols)

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

def plot_grade_distribution(
    grade_matrix: pd.DataFrame,
    title: str = "Répartition des notes",
    fixed_scale: bool = False,     # False = zoom dynamique autour des données ; True = 0–6
    y_mode: str = "auto",          # "auto" ou "class" (limite Y = taille de la classe)
    show_guides: bool = True,      # afficher lignes moyenne/médiane
):
    """
    Histogramme + KDE des notes.
    - Échelle X :
        * fixed_scale=True  -> [0, 6]
        * fixed_scale=False -> bornes dynamiques (percentiles 1%–99% élargies), bornées à [0,6]
    - Échelle Y :
        * y_mode="auto"  -> auto avec petite marge
        * y_mode="class" -> limite Y = nombre d'élèves (peut être plus joli pour une seule évaluation)
    """
    name_col = _name_col(grade_matrix)
    df_num = grade_matrix.drop(columns=[name_col], errors="ignore")
    grades = pd.to_numeric(df_num.values.ravel(), errors="coerce")
    grades = pd.Series(grades).dropna()

    if grades.empty:
        st.info("Aucune note à afficher.")
        return

    # Bornes X
    if fixed_scale:
        xmin, xmax = 0.0, 6.0
    else:
        q1, q99 = np.percentile(grades, [1, 99])
        xmin = max(0.0, q1 - 0.2)
        xmax = min(6.0, q99 + 0.2)
        if not np.isfinite(xmin) or not np.isfinite(xmax) or xmin >= xmax:
            xmin = max(0.0, float(grades.min()) - 0.2)
            xmax = min(6.0, float(grades.max()) + 0.2)
        xmin = max(0.0, xmin)
        xmax = min(6.0, xmax)

    # Bins (Freedman–Diaconis)
    n = len(grades)
    q25, q75 = np.percentile(grades, [25, 75])
    iqr = q75 - q25
    if iqr > 0 and n > 1:
        h = 2 * iqr / (n ** (1/3))
        bins = int(np.ceil((xmax - xmin) / h)) if h > 0 else 10
    else:
        bins = min(10, max(3, n))
    bins = max(3, min(60, bins))

    # Tracé
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.histplot(
        grades,
        bins=bins,
        kde=(len(grades) >= 2),
        ax=ax,
        stat="count",
        binrange=(xmin, xmax),
        edgecolor="white",
        linewidth=0.5,
    )
    ax.set_xlim(xmin, xmax)
    ax.set_title(title)
    ax.set_xlabel("Note")
    ax.set_ylabel("Effectifs")

    # Lignes guides
    if show_guides:
        mean_v = float(grades.mean())
        median_v = float(grades.median())
        ax.axvline(mean_v, linestyle="--", linewidth=1, alpha=0.9, label=f"Moyenne {mean_v:.2f}")
        ax.axvline(median_v, linestyle=":", linewidth=1, alpha=0.9, label=f"Médiane {median_v:.2f}")
        ax.legend()

    # Échelle Y
    if y_mode == "class":
        y_max = max(5, len(grade_matrix))
        ax.set_ylim(0, y_max)
    else:
        ymin, ymax = ax.get_ylim()
        ax.set_ylim(0, ymax * 1.10)

    ax.grid(True, linestyle="--", alpha=0.4)
    st.pyplot(fig)

def plot_grades_by_assignment(grade_matrix: pd.DataFrame, show_points: bool = True):
    """
    Boxplot des notes par évaluation, avec option pour afficher les points individuels.
    """
    if grade_matrix is None or grade_matrix.empty:
        st.info("Aucune donnée de notes disponible.")
        return

    name_col = _name_col(grade_matrix)
    if name_col not in grade_matrix.columns or len(grade_matrix.columns) <= 1:
        st.info("Pas assez de données pour tracer un boxplot.")
        return

    melted = (
        grade_matrix
        .drop(columns=[name_col], errors="ignore")
        .melt(var_name="Évaluation", value_name="Note")
        .dropna()
    )
    if melted.empty:
        st.info("Aucune note à afficher.")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.boxplot(x="Évaluation", y="Note", data=melted, ax=ax)
    if show_points:
        sns.stripplot(x="Évaluation", y="Note", data=melted, ax=ax, color="black", alpha=0.35, jitter=True)

    ax.set_title("Distribution des notes par évaluation")
    ax.set_ylabel("Note")
    ax.set_ylim(0, 6.0)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax.grid(True, linestyle="--", alpha=0.4)
    st.pyplot(fig)

def plot_student_progress(grade_matrix: pd.DataFrame, student_name: str):
    """
    Courbe d’évolution des notes pour un élève donné.
    """
    if grade_matrix is None or grade_matrix.empty:
        st.info("Aucune donnée de notes disponible.")
        return

    name_col = _name_col(grade_matrix)
    row = grade_matrix[grade_matrix[name_col] == student_name]
    if row.empty:
        st.warning("Élève introuvable.")
        return

    series = (
        pd.to_numeric(row.drop(columns=[name_col], errors="ignore").squeeze(), errors="coerce")
        .dropna()
    )
    if series.empty:
        st.info("Aucune note disponible pour cet élève.")
        return

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(series.index, series.values, marker="o", linewidth=2)
    ax.set_title(f"Évolution des notes — {student_name}")
    ax.set_ylabel("Note")
    ax.set_xlabel("Évaluation")
    ax.set_ylim(0, 6.0)
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    st.pyplot(fig)
