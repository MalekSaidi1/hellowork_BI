import pandas as pd
import numpy as np
import re
from datetime import datetime
from collections import Counter

# =============================================================================
# CONFIGURATION
# =============================================================================

INPUT_FILE = r"C:\Users\malee\OneDrive\Dokumente\hellowork_BI\data\offres_hellowork_full.csv"
OUTPUT_FILE = r"C:\Users\malee\OneDrive\Dokumente\hellowork_BI\data\offres_clean2.csv"

print("=" * 80)
print(">>> PREPROCESSING HELLOWORK - VERSION OPTIMISÉE <<<")
print("=" * 80)

# =============================================================================
# 1. 📥 CHARGEMENT & EXPLORATION
# =============================================================================

print("\n[1/10] 📥 Chargement des données...")
df = pd.read_csv(INPUT_FILE, encoding="utf-8")

print(f"✓ {df.shape[0]} offres × {df.shape[1]} colonnes")

# Exploration des formats uniques
print("\n🔍 EXPLORATION DES FORMATS")
print("=" * 80)
print("\n📌 Formats d'Expérience (échantillon unique):")
exp_samples = df["Expérience"].value_counts().head(20)
for exp, count in exp_samples.items():
    print(f"   {count:3d}× '{exp}'")

print("\n📌 Types de contrat:")
print(df["Type contrat"].value_counts())

# =============================================================================
# 2. 🧹 NETTOYAGE INITIAL
# =============================================================================

print("\n[2/10] 🧹 Nettoyage initial...")

df.replace(["N/A", "n/a", "", " "], np.nan, inplace=True)

df["Titre"].fillna("Poste non précisé", inplace=True)
df["Entreprise"].fillna("Entreprise confidentielle", inplace=True)
df["Localisation"].fillna("France", inplace=True)
df["Type contrat"].fillna("CDI", inplace=True)
df["Niveau d'études"].fillna("Non précisé", inplace=True)
df["Expérience"].fillna("Non précisé", inplace=True)
df["Description"].fillna("Non renseignée", inplace=True)
df["Date Publication"].fillna("01/01/2025", inplace=True)
df["Salaire"].fillna("Pas de salaire renseigné", inplace=True)

print("✓ Valeurs manquantes traitées")

# =============================================================================
# 3. 🔤 NETTOYAGE DES TEXTES
# =============================================================================

print("\n[3/10] 🔤 Nettoyage des textes...")

def clean_text(text):
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\-\']', ' ', text)
    return text.strip()

df["titre_clean"] = df["Titre"].apply(clean_text)
df["entreprise_clean"] = df["Entreprise"].apply(clean_text)
df["description_clean"] = df["Description"].apply(clean_text)

desc_with_cookies = df[df["description_clean"].str.contains("ces traceurs sont nécessaires", na=False)]
if len(desc_with_cookies) > 0:
    print(f"⚠️  {len(desc_with_cookies)} descriptions = message cookie (à re-scraper)")
else:
    print("✓ Descriptions valides")

# =============================================================================
# 4. 📍 EXTRACTION GÉOGRAPHIQUE
# =============================================================================

print("\n[4/10] 📍 Extraction géographique...")

def extract_location(loc):
    if pd.isna(loc):
        return "Non précisé", "N/A"
    loc = str(loc).strip()
    if " - " in loc:
        parts = loc.split(" - ")
        return parts[0].strip(), parts[1].strip() if len(parts) > 1 else "N/A"
    return loc, "N/A"

df[["ville", "departement"]] = df["Localisation"].apply(
    lambda x: pd.Series(extract_location(x))
)

print(f"✓ {df['ville'].nunique()} villes, {df['departement'].nunique()} départements")

# =============================================================================
# 5. 💶 PARSING SALAIRES (CORRIGÉ POUR DÉCIMALES)
# =============================================================================

print("\n[5/10] 💶 Parsing des salaires...")

def parse_salary(s):
    if pd.isna(s):
        return np.nan, np.nan, False, None
    
    s_str = str(s).lower().strip()
    
    if "pas de salaire" in s_str or s_str == "":
        return np.nan, np.nan, False, None
    
    is_estimate = "estimation" in s_str or "→" in s_str
    is_monthly = "/mois" in s_str or "mois" in s_str
    is_hourly = "/heure" in s_str or "heure" in s_str
    
    # Gérer virgules décimales pour horaires
    if is_hourly:
        s_str = re.sub(r'(\d+),(\d{1,2})(?=\D|$)', r'\1.\2', s_str)
    
    s_clean = re.sub(r'[\s\xa0]+', '', s_str)
    numbers = re.findall(r'\d+\.?\d*', s_clean)
    
    if len(numbers) < 1:
        return np.nan, np.nan, is_estimate, None
    
    nums = [float(n) for n in numbers]
    
    if len(nums) == 1:
        salary_min = salary_max = nums[0]
    else:
        salary_min = min(nums[0], nums[1])
        salary_max = max(nums[0], nums[1])
    
    if is_hourly:
        salary_min *= 35 * 47
        salary_max *= 35 * 47
        unit = "hourly"
    elif is_monthly:
        salary_min *= 12
        salary_max *= 12
        unit = "monthly"
    else:
        unit = "annual"
    
    return round(salary_min), round(salary_max), is_estimate, unit

df[["salary_min", "salary_max", "salary_estimated", "salary_unit"]] = df["Salaire"].apply(
    lambda x: pd.Series(parse_salary(x))
)

df["salary_avg"] = (df["salary_min"] + df["salary_max"]) / 2

valid_sal = df["salary_avg"].dropna()
print(f"✓ {len(valid_sal)} offres avec salaire ({len(valid_sal)/len(df)*100:.1f}%)")
if len(valid_sal) > 0:
    print(f"  Médiane: {valid_sal.median():,.0f} €/an")

# =============================================================================
# 6. 🎯 EXTRACTION D'EXPÉRIENCE AVANCÉE (BASÉE SUR VOS FORMATS)
# =============================================================================

print("\n[6/10] 🎯 Extraction de l'expérience...")

def parse_experience(exp_str):
    """
    Parse l'expérience selon les formats HelloWork observés:
    - "Exp. 1 à 7 ans"
    - "Banque • Assurance • Finance" (secteur, pas XP)
    - "Services aux Personnes" (secteur)
    - "Bac", "Bac +2" (études, pas XP)
    - "Débutant accepté"
    - "5 ans d'expérience"
    """
    if pd.isna(exp_str):
        return -1, "Non précisé", "Non précisé"
    
    exp_clean = str(exp_str).lower().strip()
    
    # Format: "Exp. X à Y ans" ou "Exp. X ans"
    match_range = re.search(r'exp[.érience]*\s*(\d+)\s*à\s*(\d+)\s*an', exp_clean)
    if match_range:
        years_min = int(match_range.group(1))
        years_max = int(match_range.group(2))
        years_avg = (years_min + years_max) / 2
        
        if years_avg <= 1:
            return 0, "Débutant", f"{years_min}-{years_max} ans"
        elif years_avg <= 3:
            return 1, "Junior", f"{years_min}-{years_max} ans"
        elif years_avg <= 6:
            return 2, "Confirmé", f"{years_min}-{years_max} ans"
        elif years_avg <= 10:
            return 3, "Senior", f"{years_min}-{years_max} ans"
        else:
            return 4, "Expert", f"{years_min}-{years_max} ans"
    
    # Format: "X ans" ou "X années"
    match_years = re.search(r'(\d+)\s*(an|année)', exp_clean)
    if match_years:
        years = int(match_years.group(1))
        
        if years == 0:
            return 0, "Débutant", f"{years} ans"
        elif years <= 2:
            return 1, "Junior", f"{years} ans"
        elif years <= 5:
            return 2, "Confirmé", f"{years} ans"
        elif years <= 10:
            return 3, "Senior", f"{years} ans"
        else:
            return 4, "Expert", f"{years} ans"
    
    # Mots-clés niveau
    keywords = {
        "débutant": (0, "Débutant"),
        "junior": (1, "Junior"),
        "confirmé": (2, "Confirmé"),
        "senior": (3, "Senior"),
        "expert": (4, "Expert"),
    }
    
    for keyword, (level, label) in keywords.items():
        if keyword in exp_clean:
            return level, label, keyword
    
    # Si contient "•" c'est probablement un secteur, pas une XP
    if "•" in exp_str or "secteur" in exp_clean:
        return -1, "Secteur mentionné", exp_str
    
    # Si c'est un niveau d'études (Bac, BEP, CAP)
    if any(kw in exp_clean for kw in ["bac", "bep", "cap", "master", "licence"]):
        return -1, "Niveau études", exp_str
    
    return -1, "Non précisé", exp_str

df[["experience_encoded", "experience_label", "experience_raw"]] = df["Expérience"].apply(
    lambda x: pd.Series(parse_experience(x))
)

print("✓ Expérience extraite et encodée")
print(f"\n📊 Distribution des niveaux:")
for level in sorted(df["experience_encoded"].unique()):
    count = (df["experience_encoded"] == level).sum()
    label = df[df["experience_encoded"] == level]["experience_label"].iloc[0] if count > 0 else "?"
    print(f"   {level:2d} ({label:12s}): {count:3d} offres")

# =============================================================================
# 7. 🔧 EXTRACTION DE COMPÉTENCES (DICTIONNAIRE ÉTENDU)
# =============================================================================

print("\n[7/10] 🔧 Extraction des compétences...")

# Dictionnaire TRÈS complet basé sur les métiers français
skills_dict = {
    # === PROGRAMMATION ===
    "python": [r"\bpython\b"],
    "java": [r"\bjava\b(?!script)"],
    "javascript": [r"\bjavascript\b", r"\bjs\b", r"\bnode\.?js\b"],
    "typescript": [r"\btypescript\b", r"\bts\b"],
    "sql": [r"\bsql\b", r"\bmysql\b", r"\bpostgresql\b", r"\bplsql\b", r"\bt-sql\b"],
    "php": [r"\bphp\b"],
    "c#": [r"\bc#\b", r"\bcsharp\b", r"\b\.net\b"],
    "ruby": [r"\bruby\b"],
    "go": [r"\bgolang\b"],
    "scala": [r"\bscala\b"],
    "kotlin": [r"\bkotlin\b"],
    "swift": [r"\bswift\b"],
    
    # === DATA & BI ===
    "power bi": [r"power\s*bi", r"powerbi"],
    "tableau": [r"\btableau\b(?!\s+(de|des))"],
    "qlik": [r"\bqlik\b", r"qliksense", r"qlikview"],
    "excel": [r"\bexcel\b", r"\bvba\b"],
    "sas": [r"\bsas\b"],
    "spss": [r"\bspss\b"],
    "looker": [r"\blooker\b"],
    "metabase": [r"\bmetabase\b"],
    
    # === ML/AI/DATA SCIENCE ===
    "machine learning": [r"machine\s+learning", r"\bml\b", r"deep\s+learning"],
    "data science": [r"data\s+science", r"data\s+scientist"],
    "tensorflow": [r"tensorflow"],
    "pytorch": [r"pytorch"],
    "scikit-learn": [r"scikit[- ]?learn", r"\bsklearn\b"],
    "pandas": [r"\bpandas\b"],
    "numpy": [r"\bnumpy\b"],
    "spark": [r"\bspark\b", r"pyspark"],
    "hadoop": [r"\bhadoop\b"],
    
    # === WEB FRONTEND ===
    "react": [r"\breact\b", r"\breactjs\b"],
    "angular": [r"\bangular\b"],
    "vue": [r"\bvue\b", r"\bvuejs\b"],
    "html": [r"\bhtml\b", r"html5"],
    "css": [r"\bcss\b", r"css3", r"sass", r"scss"],
    "bootstrap": [r"\bbootstrap\b"],
    "tailwind": [r"\btailwind\b"],
    
    # === WEB BACKEND ===
    "django": [r"\bdjango\b"],
    "flask": [r"\bflask\b"],
    "express": [r"\bexpress\b", r"expressjs"],
    "spring": [r"\bspring\b"],
    "laravel": [r"\blaravel\b"],
    "symfony": [r"\bsymfony\b"],
    "rails": [r"\brails\b", r"ruby on rails"],
    
    # === CLOUD & INFRASTRUCTURE ===
    "aws": [r"\baws\b", r"amazon\s+web\s+services"],
    "azure": [r"\bazure\b"],
    "gcp": [r"\bgcp\b", r"google\s+cloud"],
    "docker": [r"\bdocker\b"],
    "kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
    "terraform": [r"\bterraform\b"],
    "ansible": [r"\bansible\b"],
    "jenkins": [r"\bjenkins\b"],
    "gitlab ci": [r"gitlab\s*ci", r"gitlab\s*pipeline"],
    
    # === BASES DE DONNÉES ===
    "mongodb": [r"\bmongodb\b", r"\bmongo\b"],
    "redis": [r"\bredis\b"],
    "elasticsearch": [r"\belasticsearch\b"],
    "cassandra": [r"\bcassandra\b"],
    "oracle": [r"\boracle\b"],
    
    # === VERSIONNING & COLLAB ===
    "git": [r"\bgit\b"],
    "github": [r"\bgithub\b"],
    "gitlab": [r"\bgitlab\b"],
    "bitbucket": [r"\bbitbucket\b"],
    
    # === MÉTHODES & SOFT SKILLS ===
    "agile": [r"\bagile\b"],
    "scrum": [r"\bscrum\b"],
    "kanban": [r"\bkanban\b"],
    "devops": [r"\bdevops\b"],
    "ci/cd": [r"ci\s*/\s*cd", r"continuous\s+integration"],
    "tdd": [r"\btdd\b", r"test\s+driven"],
    
    # === OUTILS MÉTIER ===
    "sap": [r"\bsap\b"],
    "erp": [r"\berp\b"],
    "crm": [r"\bcrm\b"],
    "salesforce": [r"\bsalesforce\b"],
    "hubspot": [r"\bhubspot\b"],
    "jira": [r"\bjira\b"],
    "confluence": [r"\bconfluence\b"],
    
    # === CAO/DAO (BTP, Industrie) ===
    "autocad": [r"\bautocad\b"],
    "solidworks": [r"\bsolidworks\b"],
    "catia": [r"\bcatia\b"],
    "revit": [r"\brevit\b"],
    "sketchup": [r"\bsketchup\b"],
    
    # === COMPTABILITÉ & FINANCE ===
    "sage": [r"\bsage\b"],
    "cegid": [r"\bcegid\b"],
    "quickbooks": [r"\bquickbooks\b"],
    "comptabilité": [r"comptabilit[ée]"],
    
    # === MARKETING & COM ===
    "google analytics": [r"google\s+analytics"],
    "seo": [r"\bseo\b"],
    "sem": [r"\bsem\b"],
    "photoshop": [r"\bphotoshop\b"],
    "illustrator": [r"\billustrator\b"],
    "indesign": [r"\bindesign\b"],
    "figma": [r"\bfigma\b"],
    "canva": [r"\bcanva\b"],
    
    # === LANGUES (importantes pour filtres) ===
    "anglais": [r"\banglais\b", r"english"],
    "espagnol": [r"\bespagnol\b", r"spanish"],
    "allemand": [r"\ballemand\b", r"german"],
}

def extract_skills(text):
    if pd.isna(text) or text == "":
        return []
    
    text = " " + text.lower() + " "
    found = []
    
    for skill, patterns in skills_dict.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                found.append(skill)
                break
    
    return found

df["skills_list"] = (df["titre_clean"] + " " + df["description_clean"]).apply(extract_skills)
df["nb_skills"] = df["skills_list"].apply(len)
df["skills"] = df["skills_list"].apply(lambda x: ", ".join(x) if x else "aucune")

print(f"✓ {(df['nb_skills'] > 0).sum()} offres avec compétences")
print(f"  Moyenne: {df['nb_skills'].mean():.1f} compétences/offre")

all_skills = [s for sl in df["skills_list"] for s in sl]
if all_skills:
    top = Counter(all_skills).most_common(15)
    print("\n📊 Top 15 des compétences:")
    for skill, count in top:
        print(f"   {count:3d}× {skill}")

# =============================================================================
# 8. 📅 TRAITEMENT DES DATES
# =============================================================================

print("\n[8/10] 📅 Traitement des dates...")

df["date_publication"] = pd.to_datetime(df["Date Publication"], format="%d/%m/%Y", errors='coerce')
today = pd.Timestamp.now()
df["days_since_publication"] = (today - df["date_publication"]).dt.days

valid_dates = df["days_since_publication"].dropna()
if len(valid_dates) > 0:
    print(f"✓ Dates parsées (récente: {valid_dates.min()}j, ancienne: {valid_dates.max()}j)")

# =============================================================================
# 9. 🏷️ FEATURES CATÉGORIELLES ADDITIONNELLES
# =============================================================================

print("\n[9/10] 🏷️ Création de features supplémentaires...")

# Catégorie de salaire
def categorize_salary(sal):
    if pd.isna(sal):
        return "Non renseigné"
    if sal < 25000:
        return "< 25k"
    elif sal < 35000:
        return "25-35k"
    elif sal < 50000:
        return "35-50k"
    elif sal < 70000:
        return "50-70k"
    else:
        return "> 70k"

df["salary_category"] = df["salary_avg"].apply(categorize_salary)

# Remote/Télétravail (détection dans titre/description)
df["remote_possible"] = (
    df["titre_clean"].str.contains("télétravail|remote|distanciel", na=False) |
    df["description_clean"].str.contains("télétravail|remote|distanciel", na=False)
).astype(int)

# Urgence (détection mots-clés)
df["urgent"] = (
    df["titre_clean"].str.contains("urgent|immédiat|rapidement", na=False) |
    df["description_clean"].str.contains("urgent|immédiat|rapidement|dès que possible", na=False)
).astype(int)

print(f"✓ Features créées:")
print(f"  - Télétravail possible: {df['remote_possible'].sum()} offres")
print(f"  - Recrutement urgent: {df['urgent'].sum()} offres")

# =============================================================================
# 10. 💾 EXPORT
# =============================================================================

print("\n[10/10] 💾 Export des données...")

cols = [
    # ID & Brutes
    "Lien Offre", "Titre", "Entreprise", "Localisation", 
    "Type contrat", "Niveau d'études", "Expérience", 
    "Date Publication", "Salaire", "Description",
    
    # Nettoyées
    "titre_clean", "entreprise_clean", "description_clean",
    "ville", "departement",
    
    # Expérience enrichie
    "experience_encoded", "experience_label", "experience_raw",
    
    # Salaires
    "salary_min", "salary_max", "salary_avg", 
    "salary_estimated", "salary_unit", "salary_category",
    
    # Compétences
    "skills", "skills_list", "nb_skills",
    
    # Temporel
    "date_publication", "days_since_publication",
    
    # Features binaires
    "remote_possible", "urgent",
]

df_export = df[cols].copy()
df_export.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

print(f"\n✅ Fichier: {OUTPUT_FILE}")
print(f"   {len(df_export)} offres × {len(df_export.columns)} colonnes")

print("\n📊 STATISTIQUES FINALES")
print("=" * 80)
print(f"Salaires:      {(~df_export['salary_avg'].isna()).sum():3d} offres ({(~df_export['salary_avg'].isna()).sum()/len(df_export)*100:.1f}%)")
print(f"Compétences:   {(df_export['nb_skills'] > 0).sum():3d} offres ({(df_export['nb_skills'] > 0).sum()/len(df_export)*100:.1f}%)")
print(f"Télétravail:   {df_export['remote_possible'].sum():3d} offres")
print(f"Urgent:        {df_export['urgent'].sum():3d} offres")
print(f"Villes:        {df_export['ville'].nunique():3d} uniques")
print(f"Entreprises:   {df_export['entreprise_clean'].nunique():3d} uniques")

print("\n" + "=" * 80)
print(">>> PREPROCESSING TERMINÉ <<<")
print("=" * 80)