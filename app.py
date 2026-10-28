import duckdb
import pandas as pd
import joblib
import os
import streamlit as st

st.set_page_config(page_title = 'Prediccion La Liga', page_icon = "⚽", layout="wide")
st.title("⚽ Dashboard de Predicciones - La Liga (1X2)")
st.markdown("Pipeline de Machine Learning conectado a **DuckDB** y alimentado por **XGBoost / Random Forest**.")

# Ruta a la base de datos y al modelo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'futbol.duckdb')
MODEL_PATH = os.path.join(BASE_DIR, 'data', 'models', 'best_model.joblib')

@st.cache_resource
def load_model():
    if os.path.join(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None

@st.cache_data
def load_data():
    if not os.path.join(DB_PATH):
        return pd.DataFrame
    conn = duckdb.connect(DB_PATH)
    df = conn.execute("SELECT * FROM marts.fact_features ORDER BY match_date DESC LIMIT 20;").df()
    conn.close()
    return df

model = load_model()
df = load_data()

if df.empty or model is None:
    st.error("⚠️ No se encontraron datos o el modelo no está entrenado. Ejecuta `python main.py` primero.")
else:
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

    #Mapeo de predicciones si el modelo guardado usa lables numericas

    classes = list(getattr(model, 'classes_',['1','X','2']))

    df_results = df[['match_date', 'home_team_name', 'away_team_name', 'result_1x2']].copy()

    #Agregamos probabilidades
    for i, cls in enumerate(classes):
        labels_name = {0: '1', 1: 'X', 2: '2'}.get(cls, str(cls))
        df_results[f'Prob (%) {labels_name}'] = [round(p[i] * 100, 1) for p in probs]

    st.subheader("🔮 Útimas Predicciones Registradas")
    st.dataframe(df_results, use_container_width=True)

    #Muestra interactiva de un partido
    st.markdown('___')
    st.subheader(df_results, use_container_widht=True)

    # Muestra interactiva de un partido
    st.markdown("---")
    st.subheader("🔍 Inspeccionar Partido")
    partido_sel = st.selectbox("Selecciona un partido:", df['home_team_name'] + " vs " + df['away_team_name'])
    
    idx = (df['home_team_name'] + " vs " + df['away_team_name'] == partido_sel).idxmax()
    row_probs = probs[idx]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Victoria Local (1)", f"{round(row_probs[0]*100, 1)}%")
    col2.metric("Empate (X)", f"{round(row_probs[1]*100, 1)}%")
    col3.metric("Victoria Visitante (2)", f"{round(row_probs[2]*100, 1)}%") 