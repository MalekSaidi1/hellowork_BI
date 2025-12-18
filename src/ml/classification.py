import os
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import LinearSVC


# --------------------------------------------------
# 1) Chargement du fichier d'origine
# --------------------------------------------------
DATA_DIR = "data"
INPUT_FILE = os.path.join(DATA_DIR, "hellowork2_preprocessed_ml.csv")

df = pd.read_csv(INPUT_FILE)

print("Colonnes :", df.columns)
print(df.head())

# --------------------------------------------------
# 2) Garder uniquement les lignes avec target non vide
# --------------------------------------------------
df_ml = df.dropna(subset=["salary_category"]).copy()
print(f"Nombre de lignes avec target non nulle : {len(df_ml)}")

# --------------------------------------------------
# 3) Création de department_num
# --------------------------------------------------
dept = df_ml["department"].astype(str).str.strip()
mask_non_precise = dept.str.lower().eq("non précisé")

dept_num = pd.to_numeric(dept.where(~mask_non_precise, "-1"), errors="coerce")
dept_num = dept_num.fillna(-1).astype(int)
df_ml["department_num"] = dept_num

# Imputation experience_years simple (médiane) si besoin
if df_ml["experience_years"].isna().any():
    median_exp = df_ml["experience_years"].median()
    df_ml["experience_years"] = df_ml["experience_years"].fillna(median_exp)

# Imputation remote simple (0) si besoin
if df_ml["remote"].isna().any():
    df_ml["remote"] = df_ml["remote"].fillna(0)

# --------------------------------------------------
# 4) Colonne texte combinée
# --------------------------------------------------
df_ml["title_clean"] = df_ml["title_clean"].fillna("")
df_ml["description_clean"] = df_ml["description_clean"].fillna("")
df_ml["text_all"] = (df_ml["title_clean"] + " " + df_ml["description_clean"]).str.strip()

# --------------------------------------------------
# 5) Définition de X et y
# --------------------------------------------------
target_col = "salary_category"
y = df_ml[target_col]

text_col = "text_all"
numeric_features = ["department_num", "experience_years", "remote"]
categorical_features = ["category", "contract_type", "salary_unit"]

X = df_ml[[text_col] + numeric_features + categorical_features]

# --------------------------------------------------
# 6) Construction du ColumnTransformer
# --------------------------------------------------
numeric_transformer = Pipeline(
    steps=[
        ("scaler", StandardScaler())
    ]
)

categorical_transformer = Pipeline(
    steps=[
        ("onehot", OneHotEncoder(handle_unknown="ignore"))
    ]
)

text_transformer = TfidfVectorizer(
    max_features=20000,
    ngram_range=(1, 2),
    min_df=2
)

preprocessor = ColumnTransformer(
    transformers=[
        ("text", text_transformer, text_col),
        ("num", numeric_transformer, numeric_features),
        ("cat", categorical_transformer, categorical_features),
    ]
)

# --------------------------------------------------
# 7) Modèles à tester
# --------------------------------------------------
models = {
    "LogisticRegression": LogisticRegression(
        max_iter=2000
    ),
    "RandomForest": RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        n_jobs=-1
    ),
    "LinearSVC": LinearSVC(
        random_state=42
    ),
    "GradientBoosting": GradientBoostingClassifier(
        random_state=42
    ),
    
}

# --------------------------------------------------
# 8) Train / Test split
# --------------------------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# --------------------------------------------------
# 9) Entraînement + évaluation
# --------------------------------------------------
results = []

for name, clf in models.items():
    print(f"\n===== {name} (texte + structuré) =====")

    model_pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("clf", clf)
        ]
    )

    model_pipeline.fit(X_train, y_train)

    y_pred = model_pipeline.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    print(f"Accuracy : {acc:.4f}")
    print("Classification report :")
    print(classification_report(y_test, y_pred))

    results.append((name, acc))

# --------------------------------------------------
# 10) Résumé
# --------------------------------------------------
print("\nRésumé des accuracies (texte + structuré) :")
for name, acc in results:
    print(f"{name:20s} : {acc:.4f}")
