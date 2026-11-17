import json
import pandas as pd

# 1) JSON crudo (el último que generó el pipeline)
with open("data/raw/matches_PD_2024_2026-11-16.json", encoding="utf-8") as f:
    raw = json.load(f)["matches"]
raw12 = [m["status"] for m in raw if m["matchday"] == 12]
print("JSON  -> jornada 12:", pd.Series(raw12).value_counts().to_dict())

# 2) CSV local ya procesado
csv = pd.read_csv("data/powerbi/fact_matches.csv")
print("CSV   -> jornada 12:", csv.loc[csv["matchday"] == 12, "status"].value_counts().to_dict())