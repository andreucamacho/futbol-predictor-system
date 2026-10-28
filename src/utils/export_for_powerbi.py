import os
import duckdb
import pandas as pd
import joblib
from src.utils.db import get_db_connection

def export_data_for_powerbi():
    print("🔄 Exportando datos y predicciones para Power BI...")
    conn = get_db_connection()

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    export_dir = os.path.join(base_dir, 'data', 'powerbi')
    os.makedirs(export_dir, exist_ok=True)

    # 1. Exportar partidos limpios
    df_matches = conn.execute("SELECT * FROM marts.fact_matches;").df()
    df_matches.to_csv(os.path.join(export_dir, 'fact_matches.csv'), index=False)
    print("✅ Exportado: data/powerbi/fact_matches.csv")

    # 2. Exportar features y adjuntar predicciones del modelo
    df_features = conn.execute("SELECT * FROM marts.fact_features ORDER BY match_date ASC;").df()
    conn.close()

    model_path = os.path.join(base_dir, 'data', 'models', 'best_model.joblib')
    if os.path.exists(model_path):
        model = joblib.load(model_path)
        feature_cols = [
            'home_points_last_5',
            'home_avg_goals_scored_last_5',
            'home_avg_goals_conceded_last_5',
            'away_points_last_5',
            'away_avg_goals_scored_last_5',
            'away_avg_goals_conceded_last_5'
        ]
        X = df_features[feature_cols]
        df_features['pred_1x2'] = model.predict(X)
        
        probs = model.predict_proba(X)
        classes = list(getattr(model, "classes_", ['1', 'X', '2']))
        
        for i, cls in enumerate(classes):
            label_name = {0: '1', 1: 'X', 2: '2'}.get(cls, str(cls))
            df_features[f'prob_{label_name}'] = [round(p[i] * 100, 1) for p in probs]

        # Métrica de acierto
        df_features['is_correct'] = (df_features['pred_1x2'] == df_features['result_1x2']).astype(int)

    df_features.to_csv(os.path.join(export_dir, 'fact_predictions.csv'), index=False)
    print("✅ Exportado: data/powerbi/fact_predictions.csv")

if __name__ == '__main__':
    export_data_for_powerbi()