import sys
from pathlib import Path

# Añade la raíz del proyecto (futbol_predictor) a la ruta de Python
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import os
import joblib
import numpy as np
import pandas as pd
from scipy.stats import poisson
from src.utils.db import get_db_connection
from src.utils.predictions_log import aplicar_log

PROB_EN_PORCENTAJE = True   # False -> escala 0-1
N_PARTIDOS = 5

FEATURE_COLS = [
    'home_points_last_5',
    'home_avg_goals_scored_last_5',
    'home_avg_goals_conceded_last_5',
    'away_points_last_5',
    'away_avg_goals_scored_last_5',
    'away_avg_goals_conceded_last_5',
]

LABELS = {0: '1', 1: 'X', 2: '2'}


def _etiqueta(valor) -> str:
    return LABELS.get(valor, str(valor))


# ---------- Features de partidos pendientes ----------

def _historial_equipos(df_matches):
    """Una fila por equipo y partido jugado: puntos, goles a favor y en contra."""
    j = df_matches[(df_matches['status'] == 'FINISHED')
                   & df_matches['home_goals'].notna()
                   & df_matches['away_goals'].notna()]
    local = pd.DataFrame({'team_id': j['home_team_id'], 'match_date': j['match_date'],
                          'gf': j['home_goals'], 'ga': j['away_goals']})
    visit = pd.DataFrame({'team_id': j['away_team_id'], 'match_date': j['match_date'],
                          'gf': j['away_goals'], 'ga': j['home_goals']})
    h = pd.concat([local, visit], ignore_index=True)
    h['points'] = np.where(h['gf'] > h['ga'], 3, np.where(h['gf'] == h['ga'], 1, 0))
    return h.sort_values(['team_id', 'match_date'])


def _ultimos(hist, team_id, fecha):
    h = hist[(hist['team_id'] == team_id) & (hist['match_date'] < fecha)].tail(N_PARTIDOS)
    if h.empty:
        return np.nan, np.nan, np.nan
    return h['points'].sum(), h['gf'].mean(), h['ga'].mean()


def features_pendientes(df_matches):
    hist = _historial_equipos(df_matches)
    pend = df_matches[df_matches['status'] != 'FINISHED']
    filas = []
    for _, p in pend.iterrows():
        hp, hgf, hga = _ultimos(hist, p['home_team_id'], p['match_date'])
        ap, agf, aga = _ultimos(hist, p['away_team_id'], p['match_date'])
        filas.append({**p.to_dict(),
                      'home_points_last_5': hp,
                      'home_avg_goals_scored_last_5': hgf,
                      'home_avg_goals_conceded_last_5': hga,
                      'away_points_last_5': ap,
                      'away_avg_goals_scored_last_5': agf,
                      'away_avg_goals_conceded_last_5': aga})
    return pd.DataFrame(filas)


def validar_definicion(df_matches, df_features):
    """Compara mi cálculo con el de build_features en los últimos 30 jugados."""
    hist = _historial_equipos(df_matches)
    m = df_matches.set_index('match_id')
    muestra = df_features[df_features['result_1x2'].notna()].tail(30)
    fallos, total = 0, 0
    for _, r in muestra.iterrows():
        if r['match_id'] not in m.index:
            continue
        mm = m.loc[r['match_id']]
        hp, _, _ = _ultimos(hist, mm['home_team_id'], mm['match_date'])
        if pd.notna(hp) and pd.notna(r['home_points_last_5']):
            total += 1
            fallos += int(hp != r['home_points_last_5'])
    if total and fallos:
        print(f"⚠️ {fallos}/{total} partidos NO coinciden con build_features. "
              "Las features de los pendientes usan otra definición: revisa build_features.py.")
    else:
        print("✅ Las features de los pendientes siguen la misma definición que build_features.")


# ---------- Marcador probable ----------

def _marcador(xg_h, xg_a, pred, max_g=6):
    g = np.arange(max_g + 1)
    m = np.outer(poisson.pmf(g, max(xg_h, 0.1)), poisson.pmf(g, max(xg_a, 0.1)))
    i, j = np.indices(m.shape)
    permitido = {'1': i > j, 'X': i == j, '2': i < j}[pred]
    m = np.where(permitido, m, -1)
    h, a = np.unravel_index(m.argmax(), m.shape)
    return int(h), int(a)


# ---------- Exportación ----------

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

        # 2. Features (jugados + pendientes) y predicciones
        df_features = conn.execute(
            "SELECT * FROM marts.fact_features ORDER BY match_date ASC;"
        ).df()

        validar_definicion(df_matches, df_features)

        # Los pendientes se recalculan siempre desde fact_matches
        df_features = df_features[df_features['result_1x2'].notna()]
        nuevas = features_pendientes(df_matches)
        if not nuevas.empty:
            df_features = pd.concat([df_features, nuevas], ignore_index=True)
        df_features = df_features.sort_values('match_date').reset_index(drop=True)
        print(f"ℹ️ {len(nuevas)} partidos pendientes añadidos a las features")

        model_path = os.path.join(base_dir, 'data', 'models', 'best_model.joblib')
        if os.path.exists(model_path):
            model = joblib.load(model_path)
            factor = 100 if PROB_EN_PORCENTAJE else 1
            decimales = 1 if PROB_EN_PORCENTAJE else 4
            classes = list(getattr(model, "classes_", ['1', 'X', '2']))

            # Equipos sin historial (features vacías) -> sin predicción
            ok = df_features[FEATURE_COLS].notna().all(axis=1)
            X = df_features.loc[ok, FEATURE_COLS]

            df_features['pred_1x2'] = None
            df_features.loc[ok, 'pred_1x2'] = [_etiqueta(p) for p in model.predict(X)]

            probs = model.predict_proba(X)
            for i, cls in enumerate(classes):
                df_features[f'prob_{_etiqueta(cls)}'] = np.nan
                df_features.loc[ok, f'prob_{_etiqueta(cls)}'] = (probs[:, i] * factor).round(decimales)

            # Goles esperados (estimación) y marcador más probable coherente con pred_1x2
            df_features['xg_home'] = ((df_features['home_avg_goals_scored_last_5']
                                       + df_features['away_avg_goals_conceded_last_5']) / 2).round(2)
            df_features['xg_away'] = ((df_features['away_avg_goals_scored_last_5']
                                       + df_features['home_avg_goals_conceded_last_5']) / 2).round(2)
            ph, pa = [], []
            for xh, xa, p in zip(df_features['xg_home'], df_features['xg_away'], df_features['pred_1x2']):
                if pd.notna(xh) and pd.notna(xa) and p in ('1', 'X', '2'):
                    h, a = _marcador(xh, xa, p)
                    ph.append(h)
                    pa.append(a)
                else:
                    ph.append(np.nan)
                    pa.append(np.nan)
            df_features['pred_home_goals'] = ph
            df_features['pred_away_goals'] = pa

            # REGISTRO: guarda las predicciones futuras y sustituye las de los partidos
            # ya empezados por las que se hicieron ANTES de jugarse
            version = pd.Timestamp(os.path.getmtime(model_path), unit='s').strftime('%Y-%m-%d')
            df_features = aplicar_log(df_features, os.path.join(export_dir, 'prediction_log.csv'), version)

            # Acierto: DESPUÉS del registro, solo con predicciones previas al partido
            jugado = df_features['result_1x2'].notna() & df_features['pred_1x2'].notna()
            df_features['is_correct'] = pd.Series(pd.NA, index=df_features.index, dtype='Int64')
            df_features.loc[jugado, 'is_correct'] = (
                df_features.loc[jugado, 'pred_1x2'] == df_features.loc[jugado, 'result_1x2']
            ).astype(int)
        else:
            print(f"⚠️ No se encontró el modelo en {model_path}. "
                  "Se exportan las features SIN predicciones.")

        df_features.to_csv(os.path.join(export_dir, 'fact_predictions.csv'), index=False)
        print(f"✅ Exportado: data/powerbi/fact_predictions.csv ({len(df_features)} filas)")

        # 3. Dimensión de equipos con escudos
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

        # 4. Comprobaciones finales
        ult_matches = conn.execute(
            "SELECT MAX(matchday) FROM marts.fact_matches WHERE status = 'FINISHED';"
        ).fetchone()[0]
        print(f"ℹ️ Última jornada FINISHED en fact_matches: {ult_matches}")

        if 'prob_1' in df_features.columns:
            pend = df_features[df_features['result_1x2'].isna()]
            print(f"ℹ️ Partidos pendientes con predicción: {pend['prob_1'].notna().sum()}/{len(pend)}")
            if len(pend):
                print(f"ℹ️ Próxima jornada con predicción: {int(pend['matchday'].min())}")
            n_eval = int(df_features['is_correct'].notna().sum())
            print(f"ℹ️ Partidos jugados con predicción previa guardada: {n_eval}")
    finally:
        conn.close()


if __name__ == '__main__':
    export_data_for_powerbi()