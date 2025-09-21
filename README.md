# Trimesta — Gestion de notes par évaluations (Streamlit)

Trimesta est une application Streamlit pour gérer les notes d’une classe, centrée sur les **évaluations** (assignments).  
Chaque évaluation est une **colonne** dans une matrice (lignes = élèves). L’app gère les **coefficients**, les **trimestres**, les **moyennes pondérées** (élève / trimestre / globale) et propose des **visualisations**.

> **Confidentialité** : les **noms de famille sont systématiquement anonymisés** à l’import (suppression des voyelles, conservation de la première lettre). L’app fonctionne **entièrement en local**.

---

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation et lancement (Windows + VS Code)](#installation-et-lancement-windows--vs-code)
- [Organisation des données](#organisation-des-données)
- [Utilisation](#utilisation)
- [Validation et règles métier](#validation-et-règles-métier)
- [Confidentialité et exécution locale](#confidentialité-et-exécution-locale)
- [Dépannage (Windows)](#dépannage-windows)
- [Feuille de route](#feuille-de-route)
- [Licence](#licence)

---

## Fonctionnalités

- **Centrée évaluations** : chaque évaluation devient une **colonne** dans la matrice de notes.
- **Coefficient** et **trimestre** (T1, T2, T3) par évaluation.
- **Saisie groupée** : attribuer la même note à plusieurs élèves d’un coup.
- **Annuler la dernière attribution** (undo) en un clic.
- **Moyennes pondérées** :
  - par élève (tous trimestres),
  - par trimestre (T1/T2/T3),
  - globale (toutes évaluations).
- **Visualisations** :
  - histogramme global,
  - boxplot par évaluation,
  - progression d’un élève,
  - moyenne de classe par évaluation et par trimestre.
- **Tolérance FR/EN** pour les colonnes des fichiers Excel.
- **Décimales** : **virgule** ou **point** acceptés (ex. `4,5` ou `4.5`).
- **Anonymisation obligatoire du nom de famille** à l’import (suppression des voyelles, conservation de la 1re lettre).

---

## Architecture

```
repo/
├─ src/
│  ├─ trimesta.py                  # Application Streamlit (UI)
│  └─ app/
│     ├─ data_loader.py            # Import élèves (.xls/.xlsx), anonymisation, sauvegarde CSV
│     ├─ state_manager.py          # Initialisation session/matrice/métadonnées
│     ├─ data_statistics.py        # Moyennes pondérées (élève, trimestres, global)
│     ├─ data_visualization.py     # Graphiques (histogramme, boxplot, progression, synthèse trimestres)
│     └─ ui_components.py          # (optionnel / legacy)
├─ data/
│  ├─ 901.xlsx / 1BI-11.xls        # Fichiers élèves (exemples)
│  ├─ grades_matrix_901.csv        # Matrice de notes générée
│  └─ assignments_meta_901.csv     # Métadonnées (coeff, trimestre) générées
├─ .streamlit/config.toml          # (optionnel) config Streamlit locale
└─ requirements.txt
```

---

## Prérequis

- Windows 10/11
- **Python 3.9+** (3.11/3.12 OK)
- **VS Code** avec l’extension **Python**
- **Git** (si vous clonez depuis GitHub)

---

## Installation et lancement (Windows + VS Code)

### 0) Cloner le dépôt (ou dézipper)

```powershell
git clone https://github.com/<votre-utilisateur>/<votre-repo>.git
cd <votre-repo>
```
(ou téléchargez le ZIP et décompressez dans un dossier, ex. `C:\Users\<vous>\Documents\trimesta`)

### 1) Ouvrir le dossier dans VS Code

VS Code → **File > Open Folder…** → choisissez le dossier du repo.

### 2) Créer un environnement virtuel (venv)

Ouvrez le **Terminal intégré** (Terminal > New Terminal).  
Choisissez une des méthodes :

**Méthode A — Command Prompt (simple)**
```bat
py -3 -m venv .venv
.\.venv\Scripts\activate.bat
```

**Méthode B — PowerShell (il faut autoriser une fois les scripts)**
```powershell
py -3 -m venv .venv
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

**Méthode C — Sans activer la venv (appeler Python de la venv directement)**
```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m streamlit run src/trimesta.py
```

> Astuce : **Ctrl+Shift+P** → *Python: Select Interpreter* → choisissez celui de `.venv`.

### 3) Installer les dépendances

```powershell
python -m pip install -r requirements.txt
```

**requirements.txt** (recommandé) :
```
streamlit>=1.30,<2
pandas>=2.2
openpyxl>=3.1
xlrd>=2.0
matplotlib>=3.8
seaborn>=0.13
```

### 4) Lancer l’application

```powershell
python -m streamlit run src/trimesta.py
```
Le navigateur s’ouvre sur `http://localhost:8501`.

---

## Organisation des données

### Fichiers élèves (entrée)

- Dossier : `data/` (modifiable via la variable d’environnement `TRIMESTA_DATA_DIR`).
- Formats : **.xlsx** et **.xls** (les fichiers temporaires `~$...` sont ignorés).
- L’app **détecte automatiquement** la ligne d’en-tête même si des lignes libres précèdent.

Entêtes supportées (FR/EN) :
- `Prénom` / `First Name`
- `Nom` / `Last Name`
- ou `Full Name` / `Nom complet`

**Anonymisation** (obligatoire) :  
`Full Name = Prénom + Nom_anonymisé`, où le **Nom** est transformé en **retirant toutes les voyelles** tout en **gardant la première lettre** (ex. *Duprez → Dprz*, *Lévy → Lv*). Le **Prénom** n’est pas modifié.

**ID** : si une colonne `No` (ou équivalent) existe, elle est utilisée ; sinon, un ID séquentiel est généré.

### Matrice de notes (travail / sortie)

- Par classe : `grades_matrix_<classe>.csv` (créée automatiquement).
- Lignes = `Full Name`
- Colonnes = noms d’évaluations.

### Métadonnées d’évaluations (sortie)

- Par classe : `assignments_meta_<classe>.csv`
- Colonnes : `Assignment`, `Coefficient`, `Trimester` (gérées via l’UI).

---

## Utilisation

### 1) Choisir la classe
Dans la barre latérale, choisissez un fichier **.xls** ou **.xlsx** du dossier `data/`.  
Le tableau de la classe s’affiche immédiatement.

### 2) Ajouter une évaluation
- Menu « Sélectionner ou ajouter une évaluation » → « ➕ Nouvelle évaluation »
- Saisir le **nom**, le **coefficient**, et le **trimestre** (T1/T2/T3)
- Cliquer sur **Créer l’évaluation**

### 3) Attribuer des notes
- Sélectionner l’évaluation courante
- Choisir un ou plusieurs élèves
- Saisir la note (`0` à `6`, virgule ou point) → **Attribuer la note**  
Les champs se **réinitialisent automatiquement** après l’attribution.

### 4) Annuler la dernière attribution
- Ouvrir « Annuler la dernière attribution » → **Annuler cette attribution**  
Les valeurs sont supprimées et la matrice est sauvegardée.

### 5) Analyse par élève
- Choisir un élève → voir ses notes et la **moyenne pondérée** (2 décimales + affichage arrondi au **dixième**)
- Option : afficher la **progression** de l’élève.

### 6) Synthèses et visualisations
- **Synthèses par trimestre** : tableau des moyennes T1, T2, T3 + **Globale**
- Visualisations :
  - histogramme global,
  - boxplot par évaluation,
  - moyennes de classe par évaluation et **par trimestre**,
  - progression d’un élève.

---

## Validation et règles métier

- Notes acceptées : **réels de 0 à 6** (inclus).
- Séparateur décimal : **virgule** ou **point**.
- La **moyenne pondérée** utilise les coefficients des métadonnées (défaut à 1.0 si manquants).
- Si un trimestre n’a **aucune** évaluation, sa moyenne est `None`.

---

## Confidentialité et exécution locale

- L’app ne contacte **aucun service externe** : tout se passe **en local**.
- Forcer l’écoute sur localhost : créez `.streamlit/config.toml` :
```toml
[server]
address = "127.0.0.1"
port = 8501
headless = true

[browser]
gatherUsageStats = false
```

- Dossier de données configurable :
```powershell
$env:TRIMESTA_DATA_DIR = "C:\TrimestaData"
python -m streamlit run src/trimesta.py
```

- Évitez de placer `data/` dans un dossier synchronisé (OneDrive/Dropbox).  
- Chiffrez le disque (BitLocker) si données sensibles.

---

## Dépannage (Windows)

- **Le fichier .xls n’apparaît pas** : vérifiez qu’il est bien dans `data/` et que `xlrd` est installé :
```powershell
python -m pip install xlrd
```

- **Erreur PowerShell “running scripts is disabled”** : exécutez **une fois** :
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

- **`streamlit` non reconnu** : utilisez la forme module (via la venv) :
```powershell
python -m streamlit run src/trimesta.py
```

- **Port 8501 occupé** :
```powershell
python -m streamlit run src/trimesta.py --server.port 8502
```

- **Permission denied lors du clone** : clonez dans `Documents\` (évitez `C:\Program Files`).

- **“No class files found in data.”** : placez un `.xls/.xlsx` valide dans `data/`.  
  Entêtes recherchées : `Nom` + `Prénom` (ou `Last Name` + `First Name`), sinon `Full Name`.

---

## Feuille de route

- Suppression/édition d’une note **au choix** dans la matrice.
- Export PDF/Excel (élève / classe).
- Journal des modifications.
- Auth simple si multi-professeurs.

---

## Licence

À définir (ex. MIT).
