import os
import duckdb
import pandas as pd
import joblib
from src.utils.db import get_db_connection

def load_model():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    model_path = os.path.join(base_dir, 'data', 'models', 'random_forest_v1.joblib')
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"⚠️ No se encontró el modelo en: {model_path}. Ejecuta primero src.models.train")
    return joblib.load(model_path)

def predict_upcoming_matches():
    model = load_model()
    conn = get_db_connection()

    df = conn.execute("SELECT * FROM marts.fact_features ORDER BY match_date DESC LIMIT 10;").df()
    conn.close()

    if df.empty:
        print("⚠️ No hay datos para predecir.")
        return

    feature_cols = [
        'home_points_last_5',
        'home_avg_goals_scored_last_5',
        'home_avg_goals_conceded_last_5',
        'away_points_last_5',
        'away_avg_goals_scored_last_5',
        'away_avg_goals_conceded_last_5'
    ]

    X = df[feature_cols]
    preds = model.predict(X)
    probs = model.predict_proba(X)

    df['pred_1x2'] = preds
    classes = list(model.classes_)

    for i, cls in enumerate(classes):
        df[f'prob_{cls}'] = [round(p[i] * 100, 1) for p in probs]

    print("\n🔮 Muestra de Predicciones Recientes / Próximas:")
    print("="*85)
    cols_to_show = ['match_date', 'home_team_name', 'away_team_name', 'pred_1x2', 'prob_1', 'prob_X', 'prob_2', 'result_1x2']
    print(df[cols_to_show].to_string(index=False))

if __name__ == '__main__':
    predict_upcoming_matches()