import os
import duckdb
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
from src.utils.db import get_db_connection

def load_data(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    print("🔄 Cargando dataset de features desde DuckDB...")
    df = conn.execute("SELECT * FROM marts.fact_features ORDER BY match_date ASC;").df()
    print(f"✅ Se cargaron {len(df)} registros finalizados.")
    return df

def prepare_splits(df: pd.DataFrame):
    feature_cols = [
        'home_points_last_5',
        'home_avg_goals_scored_last_5',
        'home_avg_goals_conceded_last_5',
        'away_points_last_5',
        'away_avg_goals_scored_last_5',
        'away_avg_goals_conceded_last_5'
    ]
    
    X = df[feature_cols]
    y = df['result_1x2']

    split_idx = int(len(df) * 0.8)
    
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    print(f"📊 Datos de entrenamiento (Train): {len(X_train)} filas")
    print(f"📊 Datos de evaluación (Test): {len(X_test)} filas")

    return X_train, X_test, y_train, y_test, feature_cols

def run_training():
    conn = get_db_connection()
    df = load_data(conn)
    conn.close()

    if df.empty:
        print("⚠️ No hay datos en marts.fact_features. Revisa la Fase 3.")
        return

    X_train, X_test, y_train, y_test, feature_cols = prepare_splits(df)

    print("🤖 Entrenando modelo Random Forest...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print("\n" + "="*45)
    print(f"🎯 Exactitud del Modelo (Accuracy): {acc:.2%}")
    print("="*45)

    # Ruta absoluta desde la raíz del proyecto
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    models_dir = os.path.join(base_dir, 'data', 'models')
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, 'random_forest_v1.joblib')

    joblib.dump(model, model_path)
    print(f"\n💾 Modelo guardado exitosamente en: {model_path}")

if __name__ == '__main__':
    run_training()