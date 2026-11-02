from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"

MORTALITY_FILE = RAW / "Anexo1.NoFetal2019_CE_15-03-23.xlsx"
CAUSES_FILE = RAW / "Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx"
DIVIPOLA_FILE = RAW / "Divipola_CE_.xlsx"

MONTHS = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

AGE_GROUPS = [
    ("Mortalidad neonatal", 0, 4),
    ("Mortalidad infantil", 5, 6),
    ("Primera infancia", 7, 8),
    ("Niñez", 9, 10),
    ("Adolescencia", 11, 11),
    ("Juventud", 12, 13),
    ("Adultez temprana", 14, 16),
    ("Adultez intermedia", 17, 19),
    ("Vejez", 20, 24),
    ("Longevidad / Centenarios", 25, 28),
    ("Edad desconocida", 29, 29),
]


def age_category(code: int) -> str:
    for label, lower, upper in AGE_GROUPS:
        if lower <= code <= upper:
            return label
    return "Fuera de rango"


def main() -> None:
    deaths = pd.read_excel(MORTALITY_FILE, sheet_name="No_Fetales_2019")
    divipola = pd.read_excel(DIVIPOLA_FILE, sheet_name="Hoja1")
    causes = pd.read_excel(CAUSES_FILE, sheet_name="Final", header=8)

    deaths.columns = [str(column).replace("A�O", "AÑO") for column in deaths.columns]
    deaths["COD_DANE"] = deaths["COD_DANE"].astype(int).astype(str).str.zfill(5)
    deaths["COD_DEPARTAMENTO"] = deaths["COD_DEPARTAMENTO"].astype(int).astype(str).str.zfill(2)
    deaths["COD_MUERTE"] = deaths["COD_MUERTE"].astype(str).str.strip().str.upper()
    deaths["SEXO_LABEL"] = deaths["SEXO"].map({1: "Hombres", 2: "Mujeres", 3: "Indeterminado"}).fillna("Sin información")
    deaths["GRUPO_EDAD_LABEL"] = deaths["GRUPO_EDAD1"].astype(int).map(age_category)

    divipola["COD_DANE"] = divipola["COD_DANE"].astype(int).astype(str).str.zfill(5)
    divipola["COD_DEPARTAMENTO"] = divipola["COD_DEPARTAMENTO"].astype(int).astype(str).str.zfill(2)
    deaths = deaths.merge(
        divipola[["COD_DANE", "DEPARTAMENTO", "MUNICIPIO"]].drop_duplicates("COD_DANE"),
        on="COD_DANE",
        how="left",
        validate="many_to_one",
    )
    deaths["DEPARTAMENTO"] = deaths["DEPARTAMENTO"].fillna("Sin correspondencia")
    deaths["MUNICIPIO"] = deaths["MUNICIPIO"].fillna("Sin correspondencia")

    three_code, three_name = causes.columns[2], causes.columns[3]
    four_code, four_name = causes.columns[4], causes.columns[5]
    lookup_three = causes[[three_code, three_name]].rename(columns={three_code: "COD_MUERTE", three_name: "CAUSA"})
    lookup_four = causes[[four_code, four_name]].rename(columns={four_code: "COD_MUERTE", four_name: "CAUSA"})
    cause_lookup = pd.concat([lookup_four, lookup_three], ignore_index=True).dropna()
    cause_lookup["COD_MUERTE"] = cause_lookup["COD_MUERTE"].astype(str).str.strip().str.upper()
    cause_lookup = cause_lookup.drop_duplicates("COD_MUERTE")

    department_totals = (
        deaths.groupby(["COD_DEPARTAMENTO", "DEPARTAMENTO"], as_index=False)
        .size().rename(columns={"size": "TOTAL"})
    )
    monthly = deaths.groupby("MES", as_index=False).size().rename(columns={"size": "TOTAL"})
    monthly["MES_NOMBRE"] = monthly["MES"].map(MONTHS)

    violent = deaths[deaths["COD_MUERTE"].str.startswith("X95", na=False)]
    violent_cities = (
        violent.groupby(["COD_DANE", "MUNICIPIO", "DEPARTAMENTO"], as_index=False)
        .size().rename(columns={"size": "TOTAL"})
        .nlargest(5, "TOTAL")
    )

    city_totals = (
        deaths[deaths["MUNICIPIO"].ne("Sin correspondencia")]
        .groupby(["COD_DANE", "MUNICIPIO", "DEPARTAMENTO"], as_index=False)
        .size().rename(columns={"size": "TOTAL"})
        .sort_values(["TOTAL", "MUNICIPIO", "DEPARTAMENTO"])
        .head(5)
    )

    top_causes = (
        deaths.groupby("COD_MUERTE", as_index=False).size()
        .rename(columns={"size": "TOTAL"})
        .merge(cause_lookup, on="COD_MUERTE", how="left")
        .assign(CAUSA=lambda frame: frame["CAUSA"].fillna("Descripción no disponible"))
        .nlargest(10, "TOTAL")
    )

    sex_department = (
        deaths.groupby(["COD_DEPARTAMENTO", "DEPARTAMENTO", "SEXO_LABEL"], as_index=False)
        .size().rename(columns={"size": "TOTAL"})
    )
    age = (
        deaths.groupby("GRUPO_EDAD_LABEL", as_index=False).size()
        .rename(columns={"size": "TOTAL"})
    )
    age["ORDEN"] = age["GRUPO_EDAD_LABEL"].map({label: i for i, (label, _, _) in enumerate(AGE_GROUPS)})
    age = age.sort_values("ORDEN")

    filter_cube = (
        deaths.groupby(
            ["COD_DEPARTAMENTO", "DEPARTAMENTO", "SEXO_LABEL", "MES", "GRUPO_EDAD_LABEL"],
            as_index=False,
        ).size().rename(columns={"size": "TOTAL"})
    )

    outputs = {
        "department_totals.csv": department_totals,
        "monthly.csv": monthly,
        "violent_cities.csv": violent_cities,
        "low_mortality_cities.csv": city_totals,
        "top_causes.csv": top_causes[["COD_MUERTE", "CAUSA", "TOTAL"]],
        "sex_department.csv": sex_department,
        "age_groups.csv": age,
        "filter_cube.csv": filter_cube,
    }
    for name, frame in outputs.items():
        frame.to_csv(OUT / name, index=False, encoding="utf-8")

    metadata = {
        "total_deaths": int(len(deaths)),
        "departments": int(deaths["COD_DEPARTAMENTO"].nunique()),
        "municipalities": int(deaths["COD_DANE"].nunique()),
        "x95_deaths": int(len(violent)),
        "missing_municipality_matches": int(deaths["MUNICIPIO"].eq("Sin correspondencia").sum()),
        "source_year": 2019,
    }
    (OUT / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
