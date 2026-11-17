import sys
from pathlib import Path

# Añade la raíz del proyecto (futbol_predictor) a la ruta de Python
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import os
import joblib
import pandas as pd
from src.utils.db import get_db_connection

# True  -> probabilidades en escala 0-100 (como hasta ahora)
# False -> escala 0-1 (la que asumen mis medidas DAX de accuracy, Brier,
#          log loss y confianza)
PROB_EN_PORCENTAJE = True

FEATURE_COLS = [
    'home_points_last_5',
    'home_avg_goals_scored_last_5',
    'home_avg_goals_conceded_last_5',
    'away_points_last_5',
    'away_avg_goals_scored_last_5',
    'away_avg_goals_conceded_last_5',
]

# Si el modelo devuelve clases numéricas, se convierten a 1 / X / 2
LABELS = {0: '1', 1: 'X', 2: '2'}


def _etiqueta(valor) -> str:
    return LABELS.get(valor, str(valor))


def export_data_for_powerbi():
    print("🔄 Exportando datos y predicciones para Power BI...")

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    export_dir = os.path.join(base_dir, 'data', 'powerbi')
    os.makedirs(export_dir, exist_ok=True)

    conn = get_db_connection()
    try:
        # 1. Partidos limpios
        df_matches = conn.execute(
            "SELECT * FROM marts.fact_matches ORDER BY match_date ASC;"
        ).df()
        df_matches.to_csv(os.path.join(export_dir, 'fact_matches.csv'), index=False)
        print(f"✅ Exportado: data/powerbi/fact_matches.csv ({len(df_matches)} filas)")

        # 2. Features + predicciones del modelo
        df_features = conn.execute(
            "SELECT * FROM marts.fact_features ORDER BY match_date ASC;"
        ).df()

        model_path = os.path.join(base_dir, 'data', 'models', 'best_model.joblib')
        if os.path.exists(model_path):
            model = joblib.load(model_path)
            X = df_features[FEATURE_COLS]

            # Predicción convertida a 1 / X / 2 (antes podía salir 0/1/2 y
            # no coincidir nunca con result_1x2)
            df_features['pred_1x2'] = [_etiqueta(p) for p in model.predict(X)]

            probs = model.predict_proba(X)
            classes = list(getattr(model, "classes_", ['1', 'X', '2']))
            factor = 100 if PROB_EN_PORCENTAJE else 1
            decimales = 1 if PROB_EN_PORCENTAJE else 4

            for i, cls in enumerate(classes):
                df_features[f'prob_{_etiqueta(cls)}'] = (probs[:, i] * factor).round(decimales)

            # Acierto solo en partidos con resultado (los pendientes quedan vacíos)
            resultado = df_features['result_1x2']
            jugado = resultado.notna()
            df_features['is_correct'] = pd.Series(pd.NA, index=df_features.index, dtype='Int64')
            df_features.loc[jugado, 'is_correct'] = (
                df_features.loc[jugado, 'pred_1x2'] == resultado[jugado]
            ).astype(int)

            df_features['generated_at'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            print(f"⚠️ No se encontró el modelo en {model_path}. "
                  "Se exportan las features SIN predicciones.")

        df_features.to_csv(os.path.join(export_dir, 'fact_predictions.csv'), index=False)
        print(f"✅ Exportado: data/powerbi/fact_predictions.csv ({len(df_features)} filas)")

        # 3. Dimensión de equipos con escudos (desde la tabla limpia, sin duplicados)
        df_teams = conn.execute("""
            SELECT home_team_id AS team_id, home_team_name AS team_name FROM marts.fact_matches
            UNION
            SELECT away_team_id AS team_id, away_team_name AS team_name FROM marts.fact_matches
            ORDER BY team_name;
        """).df()

        df_teams['crest_url'] = df_teams['team_id'].apply(
            lambda tid: f"https://crests.football-data.org/{tid}.png"
        )
        df_teams.to_csv(os.path.join(export_dir, 'dim_teams.csv'), index=False)
        print(f"✅ Exportado: data/powerbi/dim_teams.csv ({len(df_teams)} equipos)")

        # 4. Comprobación: hasta qué jornada llega cada archivo
        ult_matches = conn.execute(
            "SELECT MAX(matchday) FROM marts.fact_matches WHERE status = 'FINISHED';"
        ).fetchone()[0]
        print(f"ℹ️ Última jornada FINISHED en fact_matches: {ult_matches}")

        if 'matchday' in df_features.columns:
            ult_feat = df_features.loc[df_features['result_1x2'].notna(), 'matchday'].max()
            print(f"ℹ️ Última jornada con resultado en fact_predictions: {ult_feat}")
            if ult_matches is not None and ult_feat != ult_matches:
                print("⚠️ Las features NO están al día con los partidos. "
                      "Revisa build_features.py antes de subir a GitHub.")
    finally:
        conn.close()


if __name__ == '__main__':
    export_data_for_powerbi()