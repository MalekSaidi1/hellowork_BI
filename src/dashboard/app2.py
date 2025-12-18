import os
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px

# --------------------------------------------------
# 1) Chargement
# --------------------------------------------------
DATA_DIR = "data"
INPUT_FILE = os.path.join(DATA_DIR, "hellowork_with_clusters.csv")

df = pd.read_csv(INPUT_FILE)

# Nettoyage
df["category"] = df["category"].fillna("Inconnu")
df["contract_type"] = df["contract_type"].fillna("Inconnu")
df["salary_category"] = df["salary_category"].fillna("Inconnu")
df["cluster"] = df["cluster"].fillna(-1)
df["remote"] = df["remote"].fillna(False)

# --------------------------------------------------
# 2) App Dash
# --------------------------------------------------
app = dash.Dash(__name__)
app.title = "Hellowork BI Dashboard"

# --------------------------------------------------
# 3) Layout
# --------------------------------------------------
app.layout = html.Div(
    style={"fontFamily": "Arial", "backgroundColor": "#f5f6fa"},
    children=[

        html.H1(
            "📊 Hellowork – Analyse BI & Classification des Offres",
            style={"textAlign": "center", "padding": "20px"}
        ),

        # ================= KPI =================
        html.Div(id="kpis", style={
            "display": "flex",
            "justifyContent": "space-around",
            "marginBottom": "20px"
        }),

        # ================= FILTRES =================
        html.Div([
            dcc.Dropdown(
                options=[{"label": c, "value": c} for c in sorted(df["category"].unique())],
                multi=True,
                placeholder="Catégorie d'emploi",
                id="filter-category"
            ),
            dcc.Dropdown(
                options=[{"label": c, "value": c} for c in sorted(df["contract_type"].unique())],
                multi=True,
                placeholder="Type de contrat",
                id="filter-contract"
            ),
            dcc.Dropdown(
                options=[{"label": f"Cluster {int(c)}", "value": int(c)}
                         for c in sorted(df["cluster"].unique())],
                multi=True,
                placeholder="Cluster métier",
                id="filter-cluster"
            ),
            dcc.Checklist(
                options=[{"label": c, "value": c}
                         for c in sorted(df["salary_category"].unique())],
                value=sorted(df["salary_category"].unique()),
                inline=True,
                id="filter-salary"
            )
        ], style={"padding": "20px"}),

        # ================= GRAPHIQUES =================
        html.Div([
            dcc.Graph(id="graph-contract"),
            dcc.Graph(id="graph-salary-category"),
            dcc.Graph(id="graph-avg-salary-contract"),
            dcc.Graph(id="graph-avg-salary-cluster"),
            dcc.Graph(id="graph-cluster-distribution"),
        ])
    ]
)

# --------------------------------------------------
# 4) CALLBACK
# --------------------------------------------------
@app.callback(
    [
        Output("kpis", "children"),
        Output("graph-contract", "figure"),
        Output("graph-salary-category", "figure"),
        Output("graph-avg-salary-contract", "figure"),
        Output("graph-avg-salary-cluster", "figure"),
        Output("graph-cluster-distribution", "figure"),
    ],
    [
        Input("filter-category", "value"),
        Input("filter-contract", "value"),
        Input("filter-cluster", "value"),
        Input("filter-salary", "value"),
    ]
)
def update_dashboard(cat, contract, cluster, salary_cat):

    dff = df.copy()

    if cat:
        dff = dff[dff["category"].isin(cat)]
    if contract:
        dff = dff[dff["contract_type"].isin(contract)]
    if cluster:
        dff = dff[dff["cluster"].isin(cluster)]
    if salary_cat:
        dff = dff[dff["salary_category"].isin(salary_cat)]

    # ---------------- KPI ----------------
    kpis = [
        html.Div(f"📌 Offres : {len(dff)}", className="kpi"),
        html.Div(f"💰 Salaire moyen : {round(dff['salary_avg'].mean(), 0)} €", className="kpi"),
        html.Div(f"🏠 Remote : {round(dff['remote'].mean()*100, 1)} %", className="kpi"),
    ]

    # ---------------- Graph 1 ----------------
    fig1 = px.bar(
        dff.groupby("contract_type").size().reset_index(name="nb"),
        x="contract_type",
        y="nb",
        title="Nombre d'offres par type de contrat"
    )

    # ---------------- Graph 2 (CLASSIFICATION) ----------------
    fig2 = px.bar(
        dff.groupby("salary_category").size().reset_index(name="nb"),
        x="salary_category",
        y="nb",
        title="Nombre d'offres par catégorie de salaire (classification)"
    )

    # ---------------- Graph 3 ----------------
    dff_salary = dff[dff["salary_avg"].notna()]
    fig3 = px.bar(
        dff_salary.groupby("contract_type")["salary_avg"].mean().reset_index(),
        x="contract_type",
        y="salary_avg",
        title="Salaire moyen par type de contrat"
    )

    # ---------------- Graph 4 ----------------
    fig4 = px.bar(
        dff_salary.groupby("cluster")["salary_avg"].mean().reset_index(),
        x="cluster",
        y="salary_avg",
        title="Salaire moyen par cluster métier"
    )

    # ---------------- Graph 5 ----------------
    fig5 = px.bar(
        dff.groupby("cluster").size().reset_index(name="nb"),
        x="cluster",
        y="nb",
        title="Répartition des offres par cluster"
    )

    return kpis, fig1, fig2, fig3, fig4, fig5


# --------------------------------------------------
# 5) Run
# --------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
