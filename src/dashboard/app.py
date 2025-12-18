import os
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px

# --------------------------------------------------
# 1) Charger les données
# --------------------------------------------------
DATA_DIR = "data"
INPUT_FILE = os.path.join(DATA_DIR, "hellowork_with_clusters.csv")

df = pd.read_csv(INPUT_FILE)

# Nettoyage minimal pour les filtres
df["category"] = df["category"].fillna("Inconnu")
df["contract_type"] = df["contract_type"].fillna("Inconnu")
df["salary_category"] = df["salary_category"].fillna("Inconnu")
df["cluster"] = df["cluster"].fillna(-1)

# --------------------------------------------------
# 2) Créer l'app Dash
# --------------------------------------------------
app = dash.Dash(__name__)
app.title = "Dashboard Hellowork"

app.layout = html.Div([
    html.H1("Dashboard Hellowork - Marché de l'emploi"),

    # Filtres
    html.Div([
        html.Div([
            html.Label("Catégorie d'emploi"),
            dcc.Dropdown(
                options=[{"label": c, "value": c} for c in sorted(df["category"].unique())],
                value=None,
                multi=True,
                id="filter-category"
            ),

            html.Label("Type de contrat"),
            dcc.Dropdown(
                options=[{"label": c, "value": c} for c in sorted(df["contract_type"].unique())],
                value=None,
                multi=True,
                id="filter-contract"
            ),

            html.Label("Cluster (texte)"),
            dcc.Dropdown(
                options=[{"label": str(int(c)), "value": int(c)} for c in sorted(df["cluster"].unique())],
                value=None,
                multi=True,
                id="filter-cluster"
            ),

            html.Label("Catégorie de salaire (réelle)"),
            dcc.Checklist(
                options=[{"label": c, "value": c} for c in sorted(df["salary_category"].unique())],
                value=sorted(df["salary_category"].unique()),
                id="filter-salary-cat",
                inline=True,
            ),
        ], style={"width": "25%", "display": "inline-block", "verticalAlign": "top", "padding": "0 20px"}),

        # Graphiques
        html.Div([
            html.Div([
                dcc.Graph(id="graph-count-by-contract"),
            ], style={"width": "49%", "display": "inline-block"}),

            html.Div([
                dcc.Graph(id="graph-count-by-salarycat"),
            ], style={"width": "49%", "display": "inline-block"}),

            html.Div([
                dcc.Graph(id="graph-avg-salary-by-contract"),
            ], style={"width": "49%", "display": "inline-block"}),

            html.Div([
                dcc.Graph(id="graph-avg-salary-by-cluster"),
            ], style={"width": "49%", "display": "inline-block"}),
        ], style={"width": "70%", "display": "inline-block", "verticalAlign": "top"}),
    ])
])

# --------------------------------------------------
# 3) Callbacks
# --------------------------------------------------
@app.callback(
    [Output("graph-count-by-contract", "figure"),
     Output("graph-count-by-salarycat", "figure"),
     Output("graph-avg-salary-by-contract", "figure"),
     Output("graph-avg-salary-by-cluster", "figure")],
    [Input("filter-category", "value"),
     Input("filter-contract", "value"),
     Input("filter-cluster", "value"),
     Input("filter-salary-cat", "value")]
)
def update_graphs(selected_categories, selected_contracts, selected_clusters, selected_salary_cats):
    dff = df.copy()

    # Appliquer les filtres
    if selected_categories:
        dff = dff[dff["category"].isin(selected_categories)]
    if selected_contracts:
        dff = dff[dff["contract_type"].isin(selected_contracts)]
    if selected_clusters:
        dff = dff[dff["cluster"].isin(selected_clusters)]
    if selected_salary_cats:
        dff = dff[dff["salary_category"].isin(selected_salary_cats)]

    # Graphique 1 : nombre d'offres par type de contrat
    count_by_contract = (
        dff.groupby("contract_type")["category"]
        .count()
        .reset_index(name="nb_offres")
    )
    fig1 = px.bar(
        count_by_contract,
        x="contract_type",
        y="nb_offres",
        title="Nombre d'offres par type de contrat"
    )

    # Graphique 2 : nombre d'offres par catégorie de salaire
    count_by_salarycat = (
        dff.groupby("salary_category")["category"]
        .count()
        .reset_index(name="nb_offres")
    )
    fig2 = px.bar(
        count_by_salarycat,
        x="salary_category",
        y="nb_offres",
        title="Nombre d'offres par catégorie de salaire"
    )

    # On garde seulement les lignes avec salaire_avg pour les graphes de salaire
    dff_salary = dff[dff["salary_avg"].notna()]

    # Graphique 3 : salaire moyen par type de contrat
    if len(dff_salary) > 0:
        avg_by_contract = (
            dff_salary.groupby("contract_type")["salary_avg"]
            .mean()
            .reset_index()
        )
        fig3 = px.bar(
            avg_by_contract,
            x="contract_type",
            y="salary_avg",
            title="Salaire moyen par type de contrat",
        )
    else:
        fig3 = px.bar(title="Salaire moyen par type de contrat (pas de données)")

    # Graphique 4 : salaire moyen par cluster
    if len(dff_salary) > 0:
        avg_by_cluster = (
            dff_salary.groupby("cluster")["salary_avg"]
            .mean()
            .reset_index()
        )
        fig4 = px.bar(
            avg_by_cluster,
            x="cluster",
            y="salary_avg",
            title="Salaire moyen par cluster",
        )
    else:
        fig4 = px.bar(title="Salaire moyen par cluster (pas de données)")

    return fig1, fig2, fig3, fig4

# --------------------------------------------------
# 4) Lancer le serveur
# --------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
