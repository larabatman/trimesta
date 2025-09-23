# Trimesta — Gestion de notes par évaluations (Streamlit)

Trimesta est une application **Streamlit** pour gérer les notes d’une classe, centrée sur les **évaluations** (assignments).  
Chaque évaluation est une **colonne** dans une matrice (lignes = élèves). L’app gère les **coefficients**, les **trimestres**, les **moyennes pondérées** (élève / trimestre / globale) et propose des **visualisations**.  
Elle fonctionne **entièrement en local** et **anonymise automatiquement** les noms de famille à l’import.

> **Confidentialité** : anonymisation **obligatoire** du nom de famille à l’import (suppression des voyelles, conservation de la première lettre). Le prénom n’est pas modifié. Aucune donnée n’est envoyée en ligne.

---

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation et lancement (Windows + VS Code)](#installation-et-lancement-windows--vs-code)
- [Organisation des données](#organisation-des-données)
- [Utilisation](#utilisation)
- [Exemple guidé pas-à-pas](#exemple-guidé-pas-à-pas)
- [Exports (Excel / PDF)](#exports-excel--pdf)
- [Sauvegardes (instantanés)](#sauvegardes-instantanés)
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
- **Renommer** ou **supprimer** une évaluation existante (avec sauvegarde automatique avant modification).
- **Moyennes pondérées** :
  - par élève (tous trimestres),
  - par trimestre (T1/T2/T3),
  - globale (toutes évaluations).
- **Visualisations** :
  - histogramme global (échelle **dynamique** centrée sur les données ou **fixe** 0–6),
  - boxplot par évaluation (avec points individuels),
  - progression d’un élève,
  - moyenne de classe par évaluation et par trimestre.
- **Exports** : génération d’un **rapport Excel** ou **PDF** personnalisable (choix des tableaux/graphes).
- **Sauvegardes** : création d’un **instantané horodaté** des fichiers de la classe (notes, méta, liste d’élèves).
- **Tolérance FR/EN** pour les colonnes des fichiers Excel (élèves + métadonnées).
- **Décimales** : **virgule** ou **point** acceptés (ex. `4,5` ou `4.5`).
- **Anonymisation obligatoire** du nom de famille à l’import (suppression des voyelles, 1re lettre conservée).

---

## Architecture

```
repo/
├─ src/
│  ├─ trimesta.py                  # Application Streamlit (UI)
│  └─ app/
│     ├─ data_loader.py            # Import élèves (.xls/.xlsx), anonymisation, sauvegarde CSV (legacy)
│     ├─ state_manager.py          # Initialisation session/matrice/métadonnées
│     ├─ data_statistics.py        # Moyennes pondérées (élève, trimestres, global)
│     ├─ data_visualization.py     # Graphiques (histogramme, boxplot, progression, synthèse trimestres)
│     ├─ export_utils.py           # Constructions Excel/PDF + helpers d’export
│     └─ ui_components.py          # (optionnel / legacy)
├─ data/
│  ├─ 901.xlsx / 1BI-11.xls        # Fichiers élèves (exemples)
│  ├─ grades_matrix_901.csv        # Matrice de notes (générée)
│  └─ assignments_meta_901.csv     # Métadonnées (coeff, trimestre) (générées)
├─ .streamlit/config.toml          # (optionnel) config thème/serveur Streamlit
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

**Méthode A — Command Prompt**
```bat
py -3 -m venv .venv
.\.venv\Scriptsctivate.bat
```

**Méthode B — PowerShell (autoriser une fois les scripts)**
```powershell
py -3 -m venv .venv
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

**Méthode C — Sans activer la venv (commande module)**
```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m streamlit run src/trimesta.py
```

> Astuce : **Ctrl+Shift+P** → *Python: Select Interpreter* → choisissez `.venv`.

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
numpy>=1.26
XlsxWriter>=3.2
```

### 4) Lancer l’application

```powershell
python -m streamlit run src/trimesta.py
```
Le navigateur s’ouvre sur `http://localhost:8501`.

---

## Organisation des données

### Fichiers élèves (entrée)

- Dossier : `data/` (modifiable via `TRIMESTA_DATA_DIR`).
- Formats : **.xlsx** et **.xls** (les fichiers temporaires `~$...` sont ignorés).
- L’app **gère les en-têtes FR/EN** : `Prénom` / `First Name`, `Nom` / `Last Name`, ou déjà `Full Name` / `Nom complet`.
- **Anonymisation** : transformation du **Nom** en retirant toutes les voyelles, **en gardant la première lettre** (ex. *Duprez → Dprz*, *Lévy → Lv*). Le **Prénom** n’est pas modifié.
- **ID** : si le fichier contient un identifiant (`No`), il est utilisé ; sinon un ID séquentiel est généré.

### Matrice de notes (travail / sortie)

- Par classe : `grades_matrix_<classe>.csv` (créée automatiquement).
- Lignes = `Full Name` (nom complet anonymisé)
- Colonnes = **noms d’évaluations** (créées via l’UI).

### Métadonnées des évaluations (sortie)

- Par classe : `assignments_meta_<classe>.csv`
- Colonnes : `Assignment`, `Coefficient`, `Trimester` (créées/complétées via l’UI).

---

## Utilisation

### 1) Choisir la classe
Dans la barre latérale, choisissez un fichier **.xls** ou **.xlsx** du dossier `data/`.  
Le tableau de la classe s’affiche immédiatement (colonnes = évaluations existantes, ou vide si aucune).

### 2) Ajouter une évaluation
- Menu « **Sélectionner ou ajouter une évaluation** » → « **➕ Nouvelle évaluation** »
- Saisir le **nom**, le **coefficient** (pondération), et le **trimestre** (T1/T2/T3)
- Cliquer sur **Créer l’évaluation**  
→ Une **colonne** est ajoutée à la matrice et une **ligne** au fichier méta.

### 3) Attribuer des notes
- Sélectionner l’évaluation courante
- Choisir un ou plusieurs élèves
- Saisir la note (`0` à `6`, virgule ou point) → **Attribuer la note**  
Les champs se **réinitialisent automatiquement** après attribution.  
Vous pouvez **Annuler la dernière attribution** depuis l’encart dédié.

### 4) Renommer / Supprimer une évaluation
- Ouvrir « **Gérer l’évaluation sélectionnée** »
- **Renommer** : saisir le nouveau nom puis **Renommer**  
- **Supprimer** : cocher la confirmation puis **Supprimer**  
L’app effectue une **sauvegarde .bak horodatée** des CSV avant modification.

### 5) Analyse par élève
- Choisir un élève → voir ses notes par évaluation et sa **moyenne pondérée** (2 décimales + arrondi au **dixième**)
- Option : afficher sa **progression** (courbe).

### 6) Synthèses et visualisations
- **Synthèses par trimestre** : tableau des moyennes T1, T2, T3 + **Globale**
- **Histogramme global** :
  - **Échelle X dynamique** (centrée sur les données) **ou fixe** 0–6
  - Échelle Y **auto** ou **taille de la classe**
- **Boxplot** par évaluation (avec points individuels)
- **Moyenne par évaluation et trimestre** (courbes superposées T1/T2/T3)
- **Progression d’un élève**

---

## Exemple guidé pas-à-pas

1. Placez un fichier `data\1BI-11.xls` (ou `901.xlsx`) avec les colonnes **Prénom** / **Nom** (ou **First Name** / **Last Name**).  
   → À l’import, les noms de famille sont **anonymisés**.
2. Lancez l’app. Dans la barre latérale, sélectionnez votre classe.  
   Le tableau (vide si aucune évaluation) s’affiche.
3. Ajoutez une évaluation : « **Contrôle 1** », coefficient **1.5**, trimestre **T1**.
4. Cochez 5 élèves et attribuez-leur la note **4,5**. Répétez pour compléter.
5. Vous vous trompez sur 2 élèves ? Ouvrez **Annuler la dernière attribution** et cliquez sur **Annuler**.
6. Ouvrez **Gérer l’évaluation sélectionnée** et **renommez** « Contrôle 1 » en « Contrôle chapitre 1 ».
7. Consultez **Analyse par élève**, affichez sa **progression**.
8. Ouvrez **Synthèses par trimestre** et comparez T1/T2/T3.
9. Dans **Visualisations**, affichez l’**Histogramme** en échelle **dynamique**, puis essayez l’échelle **fixe 0–6**.
10. Dans la **barre latérale → Sauvegardes**, cliquez sur **Créer une sauvegarde maintenant**. Un dossier horodaté est créé.
11. Enfin, dans **Exporter un rapport**, cochez :
    - **Tableau des notes** et **Synthèses par trimestre**
    - **Histogramme** (échelle dynamique), **Boxplot**, **Moyenne par trimestre**
    - **Progression** pour 2 élèves  
    Cliquez sur **Exporter en PDF** (ou **Excel**) et téléchargez votre rapport.

---

## Exports (Excel / PDF)

Dans **Exporter un rapport** (en bas) :
- Choisissez les **tables** à inclure : **Tableau des notes**, **Synthèses par trimestre**.
- Choisissez les **graphes** : Histogramme (dynamique ou 0–6, Y auto ou classe), Boxplot, Moyenne par trimestre, Progression (tous / sélection).

**Excel** : un classeur multi-feuilles est généré (`Notes`, `Synthèses`, `Meta`, `Graphiques` avec images).  
**PDF** : un document multi-pages est généré (page titre, tables/graphes).

> Dépendances requises : `XlsxWriter` pour insérer les images dans Excel.

---

## Sauvegardes (instantanés)

Dans la barre latérale → **Sauvegardes** :
- **Créer une sauvegarde maintenant** : produit `data/backups/<classe>/<YYYYmmdd-HHMMSS>/` contenant :
  - `grades_matrix_<classe>.csv` (copie actuelle)
  - `assignments_meta_<classe>.csv` (copie actuelle)
  - le fichier élèves d’origine (`.xls/.xlsx`)
  - `manifest.json` (métadonnées de la sauvegarde)
- La liste des **5 dernières** sauvegardes s’affiche.

**Restaurer** : copiez les fichiers du dossier de sauvegarde vers `data/` (en remplaçant les versions actuelles).

---

## Validation et règles métier

- Notes acceptées : **réels de 0 à 6** (inclus).
- Séparateur décimal : **virgule** ou **point**.
- La **moyenne pondérée** utilise les coefficients des métadonnées (défaut à 1.0 si manquants).
- Si un trimestre n’a **aucune** évaluation, sa moyenne est `None`.

---

## Confidentialité et exécution locale

- L’app ne contacte **aucun service externe** : tout se passe **en local**.
- Forcer l’écoute sur `localhost` : créez `.streamlit/config.toml` :
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

- **Le fichier .xls n’apparaît pas** : vérifiez qu’il est dans `data/` et que **xlrd** est installé :
```powershell
python -m pip install xlrd
```

- **Erreur PowerShell “running scripts is disabled”** : exécutez **une fois** :
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

- **`streamlit` non reconnu** : utilisez la forme module :
```powershell
python -m streamlit run src/trimesta.py
```

- **Port 8501 occupé** :
```powershell
python -m streamlit run src/trimesta.py --server.port 8502
```

- **Permission denied lors du clone** : clonez dans `Documents\` (évitez `C:\Program Files`).

- **“No class files found in data.”** : placez un `.xls/.xlsx` valide dans `data/`.  
  Entêtes acceptées : `Nom` + `Prénom` (ou `Last Name` + `First Name`), sinon `Full Name`.

---

## Feuille de route

- Suppression/édition d’une note **au choix** dans la matrice.
- Export PDF/Excel (élève / classe) plus détaillé.
- Journal des modifications.
- Authentification simple si multi-professeurs.

---

## Licence

À définir (ex. MIT).
