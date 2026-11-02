from pathlib import Path
import json

import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

metadata = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))
departments = pd.read_csv(DATA / "department_totals.csv", dtype={"COD_DEPARTAMENTO": str})
monthly = pd.read_csv(DATA / "monthly.csv")
sex = pd.read_csv(DATA / "sex_department.csv", dtype={"COD_DEPARTAMENTO": str})
ages = pd.read_csv(DATA / "age_groups.csv")
causes = pd.read_csv(DATA / "top_causes.csv")
violent = pd.read_csv(DATA / "violent_cities.csv")
low = pd.read_csv(DATA / "low_mortality_cities.csv")
geojson = json.loads((DATA / "departamentos.geojson").read_text(encoding="utf-8"))

total = metadata["total_deaths"]
assert departments["TOTAL"].sum() == total
assert monthly["TOTAL"].sum() == total
assert sex["TOTAL"].sum() == total
assert ages["TOTAL"].sum() == total
assert len(departments) == len(geojson["features"]) == 33
assert len(causes) == 10 and causes["CAUSA"].ne("Descripción no disponible").all()
assert len(violent) == 5
assert len(low) == 5
assert monthly.loc[monthly["TOTAL"].idxmax(), "MES_NOMBRE"] == "Diciembre"
assert monthly.loc[monthly["TOTAL"].idxmin(), "MES_NOMBRE"] == "Febrero"

print("Validación correcta: totales conciliados, 33 territorios y tablas completas.")
