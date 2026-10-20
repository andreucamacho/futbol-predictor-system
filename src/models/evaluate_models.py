import os
import duckdb
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report
from src.utils.db import get_db_connection

def load_data(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    #Cargamos las features de la BBDD DuckDB
    print("🔄 Cargando dataset para evaluación de modelos...")
    df = conn.execute("SELECT * FROM marts.fact_features ORDER BY match_date ASC;").df()
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

    #Mapeo de labels para XGBoost (requiere valores numericos 0,1,2)
    label_map = {'1': 0, 'X': 1, '2': 2}
    inv_label_map = {0: '1', 1: 'X', 2: '2'}
    
    y = df['result_1x2'].map(label_map)

    split_idx = int(len(df) * 0.8)
    
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    return X_train, X_test, y_train, y_test, feature_cols, inv_label_map

def run_model_benchmark():
    conn = get_db_connection()
    df = load_data(conn)
    conn.close()

    if df.empty:
        print("⚠️ No hay datos en marts.fact_features.")
        return

    X_train, X_test, y_train, y_test, feature_cols, inv_label_map = prepare_splits(df)

    # Candidatos de modelos a evaluar
    models = {
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42),
        "XGBoost": XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42, eval_metric='mlogloss')
    }

    best_acc = 0.0
    best_model_name = ""
    best_model_obj = None

    print("\n" + "="*60)
    print("🏆 COMPARATIVA DE ALGORITMOS EN FASE 5")
    print("="*60)

    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)

        print(f"📊 {name:<20} | Accuracy: {acc:.2%}")
        
        if acc > best_acc:
            best_acc = acc
            best_model_name = name
            best_model_obj = model

    print("\n" + "="*60)
    print(f"🥇 MEJOR MODELO: {best_model_name} con {best_acc:.2%} de exactitud")
    print("="*60)

    # Guardar el mejor modelo encontrado
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    models_dir = os.path.join(base_dir, 'data', 'models')
    os.makedirs(models_dir, exist_ok=True)
    best_model_path = os.path.join(models_dir, 'best_model.joblib')

    joblib.dump(best_model_obj, best_model_path)
    print(f"\n💾 Mejor modelo guardado en: {best_model_path}")

if __name__ == '__main__':
    run_model_benchmark()