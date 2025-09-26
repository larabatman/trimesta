# app/backup.py
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import shutil
import json
import pandas as pd


def make_backup(
    class_name: str,
    student_file: str | Path,
    grades_file: str | Path,
    meta_file: str | Path,
    grade_matrix: pd.DataFrame | None,
    meta_df: pd.DataFrame | None,
    data_dir: str | Path = "data",
) -> Path:
    """
    Crée un dossier d’instantané :
      data/backups/<classe>/<YYYYmmdd-HHMMSS>/
    Contenu :
      - grades_matrix_<classe>.csv     (depuis DataFrame si fournie, sinon copie fichier)
      - assignments_meta_<classe>.csv  (depuis DataFrame si fournie, sinon copie fichier si existe)
      - fichier élèves (copie .xls/.xlsx)
      - manifest.json
    Retourne le Path du dossier de sauvegarde créé.
    """
    data_dir = Path(data_dir)
    student_file = Path(student_file)
    grades_file = Path(grades_file)
    meta_file = Path(meta_file)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = data_dir / "backups" / class_name / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Matrice de notes
    grades_out = backup_dir / f"grades_matrix_{class_name}.csv"
    if isinstance(grade_matrix, pd.DataFrame):
        grade_matrix.to_csv(grades_out, index=False)
    elif grades_file.exists():
        shutil.copy2(grades_file, grades_out)

    # Métadonnées d’évaluations
    meta_out = backup_dir / f"assignments_meta_{class_name}.csv"
    if isinstance(meta_df, pd.DataFrame):
        meta_df.to_csv(meta_out, index=False)
    elif meta_file.exists():
        shutil.copy2(meta_file, meta_out)

    # Fichier élèves
    if student_file.exists():
        shutil.copy2(student_file, backup_dir / student_file.name)

    # Manifest minimal
    manifest = {
        "class_name": class_name,
        "created_at": timestamp,
        "source_data_dir": str(Path(data_dir).resolve()),
        "student_file": student_file.name,
        "grades_file": f"grades_matrix_{class_name}.csv",
        "meta_file": f"assignments_meta_{class_name}.csv",
        "files": sorted([p.name for p in backup_dir.iterdir() if p.is_file()]),
    }
    with open(backup_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return backup_dir


def list_backups_for_class(class_name: str, data_dir: str | Path) -> list[Path]:
    """Retourne la liste des dossiers de sauvegardes pour une classe, triés décroissants (plus récents d’abord)."""
    base = Path(data_dir) / "backups" / class_name
    if not base.exists():
        return []
    return sorted([p for p in base.iterdir() if p.is_dir()], reverse=True)


def load_backup_manifest(backup_dir: Path) -> dict:
    """Charge manifest.json si présent, sinon renvoie un résumé minimal (date = nom du dossier, liste de fichiers)."""
    man = backup_dir / "manifest.json"
    if man.exists():
        try:
            with open(man, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "created_at": backup_dir.name,
        "files": sorted([p.name for p in backup_dir.iterdir() if p.is_file()]),
    }


def restore_backup_overwrite(backup_dir: Path, class_name: str, data_dir: str | Path) -> None:
    """
    Écrase les fichiers courants (grades/meta) de la classe avec ceux de la sauvegarde.
    Si meta absent dans la sauvegarde : reconstruit un méta basique (coefs 1.0, trimestre T1).
    """
    data_dir = Path(data_dir)

    dest_grades = data_dir / f"grades_matrix_{class_name}.csv"
    dest_meta   = data_dir / f"assignments_meta_{class_name}.csv"

    src_grades = backup_dir / f"grades_matrix_{class_name}.csv"
    src_meta   = backup_dir / f"assignments_meta_{class_name}.csv"

    if not src_grades.exists():
        raise FileNotFoundError(f"Manquant dans la sauvegarde : {src_grades.name}")

    shutil.copy2(src_grades, dest_grades)

    if src_meta.exists():
        shutil.copy2(src_meta, dest_meta)
    else:
        # Reconstruire un méta générique
        df = pd.read_csv(dest_grades, nrows=0)
        cols = [c for c in df.columns if c != "Full Name"]
        meta = pd.DataFrame({"Assignment": cols, "Coefficient": 1.0, "Trimester": "T1"})
        meta.to_csv(dest_meta, index=False)


def restore_backup_as_copy(
    backup_dir: Path,
    class_name: str,
    new_class: str,
    data_dir: str | Path,
) -> None:
    """
    Crée une copie de la sauvegarde sous un nouveau nom de classe :
      - grades_matrix_<new_class>.csv
      - assignments_meta_<new_class>.csv (ou reconstruit)
      - copie le fichier élèves en <new_class>.<ext> dans data/
    """
    data_dir = Path(data_dir)

    dest_grades = data_dir / f"grades_matrix_{new_class}.csv"
    dest_meta   = data_dir / f"assignments_meta_{new_class}.csv"

    src_grades = backup_dir / f"grades_matrix_{class_name}.csv"
    src_meta   = backup_dir / f"assignments_meta_{class_name}.csv"
    if not src_grades.exists():
        raise FileNotFoundError(f"Manquant dans la sauvegarde : {src_grades.name}")

    shutil.copy2(src_grades, dest_grades)

    if src_meta.exists():
        shutil.copy2(src_meta, dest_meta)
    else:
        df = pd.read_csv(dest_grades, nrows=0)
        cols = [c for c in df.columns if c != "Full Name"]
        meta = pd.DataFrame({"Assignment": cols, "Coefficient": 1.0, "Trimester": "T1"})
        meta.to_csv(dest_meta, index=False)

    # Copier aussi le fichier élèves pour que la classe apparaisse dans la liste des classes
    # 1) d’après le manifest
    man = load_backup_manifest(backup_dir)
    roster_name = man.get("student_file")
    roster_path = backup_dir / roster_name if roster_name else None

    # 2) fallback : 1er Excel trouvé dans le backup
    if not roster_path or not roster_path.exists():
        candidates = list(backup_dir.glob("*.xlsx")) + list(backup_dir.glob("*.xls"))
        roster_path = candidates[0] if candidates else None

    if roster_path and roster_path.exists():
        ext = roster_path.suffix or ".xlsx"
        shutil.copy2(roster_path, data_dir / f"{new_class}{ext}")
