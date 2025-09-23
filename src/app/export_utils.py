# src/app/export_utils.py
import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages


# ==========================
# Utilitaires DataFrame
# ==========================
def name_col(df: pd.DataFrame) -> str:
    """Retourne le nom de la colonne 'nom complet' (FR/EN)."""
    for c in ["Full Name", "Nom complet", "Nom Complet", "Nom"]:
        if c in df.columns:
            return c
    return "Full Name"

def sanitize_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    Copie Arrow-friendly:
    - la colonne des noms forcée en str,
    - toutes les autres colonnes converties en float (NaN si échec).
    """
    if df is None or df.empty:
        return df
    out = df.copy()
    ncol = name_col(out)
    if ncol in out.columns:
        out[ncol] = out[ncol].astype(str)
    for col in out.columns:
        if col != ncol:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


# ==========================
# Figures pour export
# ==========================
def fig_histogram(grade_matrix: pd.DataFrame, title: str, fixed_scale: bool, y_mode: str):
    """Histogramme global (avec lignes moyenne/médiane). Renvoie une figure Matplotlib (non affichée)."""
    ncol = name_col(grade_matrix)
    df_num = grade_matrix.drop(columns=[ncol], errors="ignore")
    grades = pd.to_numeric(df_num.values.ravel(), errors="coerce")
    grades = pd.Series(grades).dropna()

    fig, ax = plt.subplots(figsize=(8, 4))
    if grades.empty:
        ax.text(0.5, 0.5, "Aucune note à afficher", ha="center", va="center")
        ax.axis("off")
        return fig

    # Bornes X (zoom dynamique par défaut)
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

    # Bins (Freedman–Diaconis + garde-fous)
    n = len(grades)
    q25, q75 = np.percentile(grades, [25, 75])
    iqr = q75 - q25
    if iqr > 0 and n > 1:
        h = 2 * iqr / (n ** (1/3))
        bins = int(np.ceil((xmax - xmin) / h)) if h > 0 else 10
    else:
        bins = min(10, max(3, n))
    bins = max(3, min(60, bins))

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

    # Échelle Y
    if y_mode == "class":
        y_max = max(5, len(grade_matrix))
        ax.set_ylim(0, y_max)
    else:
        ymin, ymax = ax.get_ylim()
        ax.set_ylim(0, ymax * 1.10)

    # Guides
    mean_v = float(grades.mean())
    median_v = float(grades.median())
    ax.axvline(mean_v, linestyle="--", linewidth=1, alpha=0.9, label=f"Moyenne {mean_v:.2f}")
    ax.axvline(median_v, linestyle=":", linewidth=1, alpha=0.9, label=f"Médiane {median_v:.2f}")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    return fig


def fig_boxplot(grade_matrix: pd.DataFrame):
    """Boxplot + points par évaluation. Renvoie une figure Matplotlib (non affichée)."""
    ncol = name_col(grade_matrix)
    fig, ax = plt.subplots(figsize=(10, 5))
    if ncol not in grade_matrix.columns or len(grade_matrix.columns) <= 1:
        ax.text(0.5, 0.5, "Pas assez de données pour un boxplot", ha="center", va="center")
        ax.axis("off")
        return fig

    melted = (
        grade_matrix
        .drop(columns=[ncol], errors="ignore")
        .melt(var_name="Évaluation", value_name="Note")
        .dropna()
    )
    if melted.empty:
        ax.text(0.5, 0.5, "Aucune note à afficher", ha="center", va="center")
        ax.axis("off")
        return fig

    sns.boxplot(x="Évaluation", y="Note", data=melted, ax=ax)
    sns.stripplot(x="Évaluation", y="Note", data=melted, ax=ax, color="black", alpha=0.35, jitter=True)
    ax.set_title("Distribution des notes par évaluation")
    ax.set_ylabel("Note")
    ax.set_ylim(0, 6.0)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax.grid(True, linestyle="--", alpha=0.4)
    return fig


def _normalize_meta(meta_df: pd.DataFrame) -> pd.DataFrame:
    """Normalise (FR/EN) les colonnes de méta pour l’export trimestriel."""
    meta = meta_df.copy() if isinstance(meta_df, pd.DataFrame) else pd.DataFrame()
    if not meta.empty:
        low = {str(c).strip().lower(): c for c in meta.columns}
        def pick(cands, target):
            for c in cands:
                k = c.lower()
                if k in low:
                    meta.rename(columns={low[k]: target}, inplace=True)
                    break
    for col in ["Assignment", "Coefficient", "Trimester"]:
        if col not in meta.columns:
            meta[col] = pd.Series(dtype="object")
    return meta[["Assignment", "Coefficient", "Trimester"]]

def fig_class_trimester_summary(grade_matrix: pd.DataFrame, meta_df: pd.DataFrame):
    """Courbes de moyenne par évaluation et trimestre. Renvoie une figure."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ncol = name_col(grade_matrix)

    meta = _normalize_meta(meta_df)
    exist = [c for c in grade_matrix.columns if c != ncol]
    meta = meta[meta["Assignment"].isin(exist)].copy()

    if meta.empty:
        ax.text(0.5, 0.5, "Aucune évaluation associée à un trimestre", ha="center", va="center")
        ax.axis("off")
        return fig

    colors = {"T1": "#8ecae6", "T2": "#ffb703", "T3": "#90be6d"}
    plotted_any = False
    for trimester in ["T1", "T2", "T3"]:
        cols = meta.loc[meta["Trimester"] == trimester, "Assignment"].tolist()
        if cols:
            sub = grade_matrix[cols].apply(pd.to_numeric, errors="coerce")
            means = sub.mean(skipna=True).reindex(cols)
            ax.plot(means.index, means.values, marker="o", linewidth=2, color=colors.get(trimester, None),
                    label=f"Moyenne {trimester}")
            plotted_any = True

    if not plotted_any:
        ax.text(0.5, 0.5, "Aucune évaluation associée à un trimestre", ha="center", va="center")
        ax.axis("off")
        return fig

    ax.set_title("Moyenne de la classe par évaluation et par trimestre")
    ax.set_ylabel("Note")
    ax.set_ylim(0, 6.5)
    ax.grid(True, linestyle="--", alpha=0.5)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax.legend(title="Trimestre")
    return fig


def fig_student_progress(grade_matrix: pd.DataFrame, student_name: str):
    """Courbe d’évolution pour un élève. Renvoie une figure."""
    fig, ax = plt.subplots(figsize=(8, 4))
    ncol = name_col(grade_matrix)
    row = grade_matrix[grade_matrix[ncol] == student_name]
    if row.empty:
        ax.text(0.5, 0.5, "Élève introuvable", ha="center", va="center")
        ax.axis("off")
        return fig
    series = (
        pd.to_numeric(row.drop(columns=[ncol], errors="ignore").squeeze(), errors="coerce")
        .dropna()
    )
    if series.empty:
        ax.text(0.5, 0.5, "Aucune note pour cet élève", ha="center", va="center")
        ax.axis("off")
        return fig
    ax.plot(series.index, series.values, marker="o", linewidth=2)
    ax.set_title(f"Évolution des notes — {student_name}")
    ax.set_ylabel("Note")
    ax.set_xlabel("Évaluation")
    ax.set_ylim(0, 6.0)
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    return fig


def fig_table(df: pd.DataFrame, title: str = "", max_rows: int = 25, max_cols: int = 12):
    """Rend un DataFrame en image (table matplotlib) pour insertion PDF."""
    disp = df.copy()
    if max_rows and len(disp) > max_rows:
        disp = disp.head(max_rows)
    if max_cols and disp.shape[1] > max_cols:
        disp = disp.iloc[:, :max_cols]
    fig, ax = plt.subplots(figsize=(8.27, 11.69))  # A4 portrait
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=14, pad=12)
    tbl = ax.table(cellText=disp.values, colLabels=disp.columns, loc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    tbl.scale(1, 1.2)
    return fig


# ==========================
# Builders (renvoient des bytes)
# ==========================
def build_excel_report(
    grade_matrix: pd.DataFrame,
    meta_df: pd.DataFrame,
    class_name: str,
    *,
    include_grades: bool = True,
    include_trimester_table: bool = True,
    include_hist: bool = False,
    hist_fixed: bool = False,
    hist_y_mode: str = "auto",
    include_box: bool = False,
    include_trim_plot: bool = False,
    include_progress: bool = False,
    progress_students: list[str] | None = None,
) -> bytes:
    """Construit un classeur Excel (multi-feuilles) et renvoie son contenu binaire."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        # Feuilles de tables
        if include_grades:
            sanitize_for_display(grade_matrix).to_excel(writer, sheet_name="Notes", index=False)
        if include_trimester_table and isinstance(meta_df, pd.DataFrame):
            from app.data_statistics import compute_trimester_averages
            tri = compute_trimester_averages(grade_matrix, meta_df)
            tri.to_excel(writer, sheet_name="Synthèses", index=False)
        if isinstance(meta_df, pd.DataFrame) and not meta_df.empty:
            meta_df.to_excel(writer, sheet_name="Meta", index=False)

        # Feuille Graphiques
        book = writer.book
        graphs_sheet = book.add_worksheet("Graphiques")
        row_cursor, col_cursor = 1, 1

        def _insert_fig(fig, title):
            nonlocal row_cursor, col_cursor
            img = io.BytesIO()
            fig.savefig(img, format="png", dpi=200, bbox_inches="tight")
            img.seek(0)
            graphs_sheet.write(row_cursor - 1, col_cursor, title)
            graphs_sheet.insert_image(row_cursor, col_cursor, title + ".png", {"image_data": img})
            plt.close(fig)
            row_cursor += 32  # décalage vertical

        # Graphiques selon options
        if include_hist:
            fig = fig_histogram(
                grade_matrix,
                title=f"Répartition des notes — Classe {class_name}",
                fixed_scale=hist_fixed,
                y_mode=hist_y_mode,
            )
            _insert_fig(fig, "Histogramme")
        if include_box:
            fig = fig_boxplot(grade_matrix)
            _insert_fig(fig, "Boxplot par évaluation")
        if include_trim_plot:
            fig = fig_class_trimester_summary(grade_matrix, meta_df)
            _insert_fig(fig, "Moyenne par évaluation et trimestre")
        if include_progress and progress_students:
            for s in progress_students:
                fig = fig_student_progress(grade_matrix, s)
                _insert_fig(fig, f"Progression — {s}")

    return buffer.getvalue()


def build_pdf_report(
    grade_matrix: pd.DataFrame,
    meta_df: pd.DataFrame,
    class_name: str,
    *,
    include_grades: bool = True,
    include_trimester_table: bool = True,
    include_hist: bool = False,
    hist_fixed: bool = False,
    hist_y_mode: str = "auto",
    include_box: bool = False,
    include_trim_plot: bool = False,
    include_progress: bool = False,
    progress_students: list[str] | None = None,
) -> bytes:
    """Construit un PDF multi-pages et renvoie son contenu binaire."""
    pdf_buffer = io.BytesIO()
    with PdfPages(pdf_buffer) as pdf:
        # Page titre
        title_df = pd.DataFrame({"Classe": [class_name], "Généré le": [datetime.now().strftime("%Y-%m-%d %H:%M")]})
        fig = fig_table(title_df, title="Rapport Trimesta", max_rows=2, max_cols=2)
        pdf.savefig(fig); plt.close(fig)

        # Tables
        if include_grades:
            fig = fig_table(sanitize_for_display(grade_matrix), title="Tableau des notes (aperçu)")
            pdf.savefig(fig); plt.close(fig)
        if include_trimester_table and isinstance(meta_df, pd.DataFrame):
            from app.data_statistics import compute_trimester_averages
            tri = compute_trimester_averages(grade_matrix, meta_df)
            fig = fig_table(tri, title="Synthèses par trimestre")
            pdf.savefig(fig); plt.close(fig)

        # Graphiques
        if include_hist:
            fig = fig_histogram(
                grade_matrix,
                title=f"Répartition des notes — Classe {class_name}",
                fixed_scale=hist_fixed,
                y_mode=hist_y_mode,
            )
            pdf.savefig(fig); plt.close(fig)

        if include_box:
            fig = fig_boxplot(grade_matrix)
            pdf.savefig(fig); plt.close(fig)

        if include_trim_plot:
            fig = fig_class_trimester_summary(grade_matrix, meta_df)
            pdf.savefig(fig); plt.close(fig)

        if include_progress and progress_students:
            for s in progress_students:
                fig = fig_student_progress(grade_matrix, s)
                pdf.savefig(fig); plt.close(fig)

    return pdf_buffer.getvalue()
