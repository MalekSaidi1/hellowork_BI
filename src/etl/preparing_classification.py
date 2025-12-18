import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import os
# --------------------------------------------------
# 1) Chargement des données
# --------------------------------------------------
DATA_DIR = "data"
INPUT_FILE = os.path.join(DATA_DIR, "hellowork2_preprocessed_ml.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "hellowork_classification_prepared.csv")

df = pd.read_csv(INPUT_FILE)
print(df.head())
print(df.columns)

# --------------------------------------------------
# 2) Garder uniquement les lignes avec target non vide
# --------------------------------------------------
df_clf = df.dropna(subset=["salary_category"]).copy()
print(f"Nombre de lignes après filtre target non nulle : {len(df_clf)}")

# --------------------------------------------------
# 3) Traitement de department -> department_num
#    - 'Non précisé' -> -1
#    - le reste -> int
# --------------------------------------------------
dept = df_clf["department"].astype(str).str.strip()
mask_non_precise = dept.str.lower().eq("non précisé")

# Remplacer "Non précisé" par "-1", puis convertir le reste en numérique
dept_num = pd.to_numeric(dept.where(~mask_non_precise, "-1"), errors="coerce")
dept_num = dept_num.fillna(-1).astype(int)

df_clf["department_num"] = dept_num

# --------------------------------------------------
# 4) Imputation experience_years + standardisation plus tard
# --------------------------------------------------
if df_clf["experience_years"].isna().any():
    median_exp = df_clf["experience_years"].median()
    df_clf["experience_years"] = df_clf["experience_years"].fillna(median_exp)

# --------------------------------------------------
# 5) remote : déjà binaire, on comble les NaN par 0 au cas où
# --------------------------------------------------
if df_clf["remote"].isna().any():
    df_clf["remote"] = df_clf["remote"].fillna(0)

# --------------------------------------------------
# 6) One-hot encoding : category, contract_type, salary_unit
# --------------------------------------------------
cat_dummies = pd.get_dummies(df_clf["category"], prefix="category")
contract_dummies = pd.get_dummies(df_clf["contract_type"], prefix="contract_type")
unit_dummies = pd.get_dummies(df_clf["salary_unit"], prefix="salary_unit")

# --------------------------------------------------
# 7) Standardisation des numériques : department_num, experience_years, remote
# --------------------------------------------------
scaler = StandardScaler()
num_cols = ["department_num", "experience_years", "remote"]
num_scaled = scaler.fit_transform(df_clf[num_cols])

num_scaled_df = pd.DataFrame(
    num_scaled,
    columns=[f"std_{c}" for c in num_cols],
    index=df_clf.index
)

# --------------------------------------------------
# 8) Construction du DataFrame final pour la classification
# --------------------------------------------------
base_cols = [
    "category",
    "contract_type",
    "remote",
    "experience_years",
    "department",
    "department_num",
    "salary_unit",
    "salary_category",  # target
]

prepared_clf = pd.concat(
    [
        df_clf[base_cols].reset_index(drop=True),
        num_scaled_df.reset_index(drop=True),
        cat_dummies.reset_index(drop=True),
        contract_dummies.reset_index(drop=True),
        unit_dummies.reset_index(drop=True),
    ],
    axis=1,
)

print("Aperçu du dataset préparé :")
print(prepared_clf.head())
print("Shape :", prepared_clf.shape)

# --------------------------------------------------
# 9) Sauvegarde du dataset préparé
# --------------------------------------------------
prepared_clf.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")