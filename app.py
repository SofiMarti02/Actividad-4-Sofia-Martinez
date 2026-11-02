from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dash_table, dcc, html


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

COLORS = {
    "navy": "#132238",
    "blue": "#1D4ED8",
    "cyan": "#0891B2",
    "gold": "#F59E0B",
    "red": "#DC2626",
    "paper": "#F5F7FB",
    "white": "#FFFFFF",
    "muted": "#64748B",
}

MONTH_ORDER = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
AGE_ORDER = [
    "Mortalidad neonatal", "Mortalidad infantil", "Primera infancia", "Niñez",
    "Adolescencia", "Juventud", "Adultez temprana", "Adultez intermedia",
    "Vejez", "Longevidad / Centenarios", "Edad desconocida",
]


def read_csv(name: str, **kwargs) -> pd.DataFrame:
    return pd.read_csv(DATA / name, dtype={"COD_DEPARTAMENTO": str, "COD_DANE": str}, **kwargs)


department_totals = read_csv("department_totals.csv")
violent_cities = read_csv("violent_cities.csv")
low_cities = read_csv("low_mortality_cities.csv")
top_causes = read_csv("top_causes.csv")
sex_department = read_csv("sex_department.csv")
filter_cube = read_csv("filter_cube.csv")
metadata = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))
geojson = json.loads((DATA / "departamentos.geojson").read_text(encoding="utf-8"))


def style_figure(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=30, r=22, t=58, b=38),
        paper_bgcolor=COLORS["white"],
        plot_bgcolor=COLORS["white"],
        font=dict(family="Inter, system-ui, sans-serif", color=COLORS["navy"], size=13),
        title=dict(font=dict(size=18, color=COLORS["navy"]), x=0.02, xanchor="left"),
        hoverlabel=dict(bgcolor=COLORS["navy"], font_color="white"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=False, linecolor="#E2E8F0")
    fig.update_yaxes(gridcolor="#E2E8F0", zeroline=False)
    return fig


map_figure = px.choropleth(
    department_totals,
    geojson=geojson,
    locations="COD_DEPARTAMENTO",
    featureidkey="properties.divipola_dep",
    color="TOTAL",
    hover_name="DEPARTAMENTO",
    hover_data={"COD_DEPARTAMENTO": False, "TOTAL": ":,d"},
    color_continuous_scale=["#DBEAFE", "#60A5FA", "#1D4ED8", "#132238"],
    labels={"TOTAL": "Defunciones"},
    title="Distribución total por departamento",
)
map_figure.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
map_figure.update_layout(coloraxis_colorbar=dict(title="Defunciones", thickness=12), dragmode=False)
style_figure(map_figure, 520)

violent_figure = px.bar(
    violent_cities.sort_values("TOTAL"),
    x="TOTAL", y="MUNICIPIO", orientation="h",
    color="TOTAL", color_continuous_scale=["#FECACA", "#DC2626"],
    custom_data=["DEPARTAMENTO"],
    title="5 ciudades con más homicidios por armas de fuego (X95)",
    labels={"TOTAL": "Defunciones", "MUNICIPIO": "Ciudad"},
)
violent_figure.update_traces(hovertemplate="<b>%{y}</b><br>%{customdata[0]}<br>Casos: %{x:,}<extra></extra>")
violent_figure.update_layout(coloraxis_showscale=False)
style_figure(violent_figure)

pie_figure = px.pie(
    low_cities,
    values="TOTAL", names="MUNICIPIO", hole=0.52,
    color_discrete_sequence=px.colors.qualitative.Safe,
    custom_data=["DEPARTAMENTO"],
    title="10 ciudades con menor número de defunciones registradas",
)
pie_figure.update_traces(textposition="inside", textinfo="label+value", hovertemplate="<b>%{label}</b><br>%{customdata[0]}<br>Defunciones: %{value}<extra></extra>")
style_figure(pie_figure)

sex_figure = px.bar(
    sex_department,
    x="DEPARTAMENTO", y="TOTAL", color="SEXO_LABEL",
    barmode="stack",
    color_discrete_map={"Hombres": COLORS["blue"], "Mujeres": COLORS["cyan"], "Indeterminado": COLORS["gold"]},
    category_orders={"SEXO_LABEL": ["Hombres", "Mujeres", "Indeterminado"]},
    title="Defunciones por sexo y departamento",
    labels={"TOTAL": "Defunciones", "DEPARTAMENTO": "Departamento", "SEXO_LABEL": "Sexo"},
)
sex_figure.update_xaxes(tickangle=-55)
style_figure(sex_figure, 500)


app = Dash(__name__, title="Mortalidad Colombia 2019", update_title="Actualizando…")
server = app.server


def metric(label: str, value: str, note: str) -> html.Div:
    return html.Div([html.P(label, className="metric-label"), html.H3(value), html.P(note, className="metric-note")], className="metric")


app.layout = html.Div([
    html.Header([
        html.Div([
            html.P("DANE · Estadísticas Vitales", className="eyebrow"),
            html.H1("Mortalidad en Colombia, 2019"),
            html.P("Exploración interactiva de las defunciones no fetales según territorio, tiempo, causa, sexo y ciclo de vida.", className="subtitle"),
        ], className="hero-copy"),
        html.Div("2019", className="year-badge"),
    ], className="hero"),
    html.Main([
        html.Section([
            metric("Defunciones registradas", f"{metadata['total_deaths']:,}", "Registros no fetales"),
            metric("Departamentos", f"{metadata['departments']}", "Incluye Bogotá D.C."),
            metric("Municipios con registros", f"{metadata['municipalities']:,}", "Según lugar de ocurrencia"),
            metric("Homicidios X95", f"{metadata['x95_deaths']:,}", "Armas de fuego"),
        ], className="metrics"),
        html.Section([
            html.Div([html.P("Filtros del análisis temporal y etario", className="filter-title"), html.P("El mapa y las comparaciones nacionales se mantienen como referencia.", className="filter-note")]),
            html.Div([html.Label("Departamento"), dcc.Dropdown(id="department-filter", options=[{"label": "Toda Colombia", "value": "ALL"}] + [{"label": row.DEPARTAMENTO.title(), "value": row.COD_DEPARTAMENTO} for row in department_totals.sort_values("DEPARTAMENTO").itertuples()], value="ALL", clearable=False)]),
            html.Div([html.Label("Sexo"), dcc.Dropdown(id="sex-filter", options=[{"label": "Todos", "value": "ALL"}, {"label": "Hombres", "value": "Hombres"}, {"label": "Mujeres", "value": "Mujeres"}, {"label": "Indeterminado", "value": "Indeterminado"}], value="ALL", clearable=False)]),
        ], className="filters"),
        html.Section([html.Div(dcc.Graph(figure=map_figure, config={"displayModeBar": False}), className="card wide")], className="grid"),
        html.Section([
            html.Div(dcc.Graph(id="monthly-chart", config={"displayModeBar": False}), className="card"),
            html.Div(dcc.Graph(id="age-chart", config={"displayModeBar": False}), className="card"),
            html.Div(dcc.Graph(figure=violent_figure, config={"displayModeBar": False}), className="card"),
            html.Div(dcc.Graph(figure=pie_figure, config={"displayModeBar": False}), className="card"),
            html.Div(dcc.Graph(figure=sex_figure, config={"displayModeBar": False}), className="card wide"),
            html.Div([
                html.Div([html.H2("10 principales causas de muerte"), html.P("Códigos CIE-10 de cuatro caracteres, ordenados por número de casos.")], className="table-heading"),
                dash_table.DataTable(
                    data=top_causes.to_dict("records"),
                    columns=[{"name": "Código", "id": "COD_MUERTE"}, {"name": "Causa", "id": "CAUSA"}, {"name": "Total", "id": "TOTAL", "type": "numeric", "format": {"specifier": ",d"}}],
                    style_as_list_view=True,
                    style_header={"backgroundColor": COLORS["navy"], "color": "white", "fontWeight": 700, "border": "none", "textAlign": "left"},
                    style_cell={"padding": "13px 14px", "fontFamily": "Inter, system-ui, sans-serif", "fontSize": "13px", "whiteSpace": "normal", "height": "auto", "borderBottom": "1px solid #E2E8F0", "textAlign": "left"},
                    style_cell_conditional=[{"if": {"column_id": "COD_MUERTE"}, "width": "12%", "fontWeight": 700}, {"if": {"column_id": "TOTAL"}, "width": "14%", "textAlign": "right", "fontWeight": 700}],
                    style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#F8FAFC"}],
                ),
            ], className="card wide table-card"),
        ], className="grid"),
        html.Section([
            html.H2("Notas metodológicas"),
            html.Ul([
                html.Li("Unidad de análisis: defunciones no fetales ocurridas en Colombia durante 2019."),
                html.Li("La categoría X95 se identifica por el prefijo del código CIE-10 de cuatro caracteres."),
                html.Li("La visualización de menor mortalidad usa conteos absolutos. No representa una tasa porque los archivos suministrados no incluyen población municipal."),
                html.Li("Los grupos etarios siguen los rangos de GRUPO_EDAD1 definidos en la consigna."),
            ]),
        ], className="method"),
    ]),
    html.Footer("Fuente: DANE, Estadísticas Vitales 2019. Elaboración académica con Python, Plotly y Dash."),
], className="page")


@app.callback(
    Output("monthly-chart", "figure"),
    Output("age-chart", "figure"),
    Input("department-filter", "value"),
    Input("sex-filter", "value"),
)
def update_filtered_charts(department: str, sex: str):
    frame = filter_cube.copy()
    if department != "ALL":
        frame = frame[frame["COD_DEPARTAMENTO"] == department]
    if sex != "ALL":
        frame = frame[frame["SEXO_LABEL"] == sex]

    monthly = frame.groupby("MES", as_index=False)["TOTAL"].sum()
    monthly["MES_NOMBRE"] = monthly["MES"].map(dict(enumerate(MONTH_ORDER, start=1)))
    monthly = monthly.set_index("MES").reindex(range(1, 13), fill_value=0).reset_index()
    monthly["MES_NOMBRE"] = monthly["MES"].map(dict(enumerate(MONTH_ORDER, start=1)))
    monthly_figure = px.line(monthly, x="MES_NOMBRE", y="TOTAL", markers=True, title="Defunciones por mes", labels={"MES_NOMBRE": "Mes", "TOTAL": "Defunciones"})
    monthly_figure.update_traces(line=dict(color=COLORS["blue"], width=3), marker=dict(size=8, color=COLORS["gold"]), fill="tozeroy", fillcolor="rgba(29,78,216,0.08)", hovertemplate="<b>%{x}</b><br>Defunciones: %{y:,}<extra></extra>")
    monthly_figure.update_xaxes(categoryorder="array", categoryarray=MONTH_ORDER, tickangle=-35)
    style_figure(monthly_figure)

    ages = frame.groupby("GRUPO_EDAD_LABEL", as_index=False)["TOTAL"].sum()
    ages["GRUPO_EDAD_LABEL"] = pd.Categorical(ages["GRUPO_EDAD_LABEL"], categories=AGE_ORDER, ordered=True)
    ages = ages.sort_values("GRUPO_EDAD_LABEL")
    age_figure = px.bar(ages, x="GRUPO_EDAD_LABEL", y="TOTAL", title="Distribución por ciclo de vida", labels={"GRUPO_EDAD_LABEL": "Grupo etario", "TOTAL": "Defunciones"}, color="TOTAL", color_continuous_scale=["#CFFAFE", "#0891B2", "#132238"])
    age_figure.update_layout(coloraxis_showscale=False)
    age_figure.update_traces(hovertemplate="<b>%{x}</b><br>Defunciones: %{y:,}<extra></extra>")
    age_figure.update_xaxes(tickangle=-45, categoryorder="array", categoryarray=AGE_ORDER)
    style_figure(age_figure)
    return monthly_figure, age_figure


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
