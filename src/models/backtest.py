import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import log_loss
from src.utils.db import get_db_connection
from src.utils.export_for_powerbi import FEATURE_COLS, PROB_EN_PORCENTAJE, _marcador
from src.utils.predictions_log import upsert_log, LOG_COLS

MAPA = {'1': 0, 'X': 1, '2': 2}
INV = {v: k for k, v in MAPA.items()}


def run_backtest(min_train=80):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    export_dir = os.path.join(base_dir, 'data', 'powerbi')
    os.makedirs(export_dir, exist_ok=True)

    conn = get_db_connection()
    try:
        feats = conn.execute("SELECT * FROM marts.fact_features ORDER BY match_date").df()
    finally:
        conn.close()

    feats['match_date'] = pd.to_datetime(feats['match_date'])
    jug = feats[feats['result_1x2'].isin(MAPA)].dropna(subset=FEATURE_COLS).copy()
    jug['y'] = jug['result_1x2'].map(MAPA).astype(int)

    modelo_base = joblib.load(os.path.join(base_dir, 'data', 'models', 'best_model.joblib'))
    claves = ['season_id', 'matchday'] if 'season_id' in jug.columns else ['matchday']
    jug['bloque'] = jug.groupby(claves)['match_date'].transform('min')

    factor = 100 if PROB_EN_PORCENTAJE else 1
    dec = 1 if PROB_EN_PORCENTAJE else 4
    filas, resumen = [], []

    for inicio in sorted(jug['bloque'].unique()):
        train = jug[jug['match_date'] < inicio]
        test = jug[jug['bloque'] == inicio]
        if len(train) < min_train or train['y'].nunique() < 3:
            continue

        m = clone(modelo_base)
        m.fit(train[FEATURE_COLS], train['y'])
        p = np.zeros((len(test), 3))
        p[:, list(m.classes_)] = m.predict_proba(test[FEATURE_COLS])
        pred = p.argmax(axis=1)

        t = test.copy()
        t['pred_1x2'] = [INV[i] for i in pred]
        t['prob_1'], t['prob_X'], t['prob_2'] = [(p[:, i] * factor).round(dec) for i in range(3)]
        t['xg_home'] = ((t['home_avg_goals_scored_last_5'] + t['away_avg_goals_conceded_last_5']) / 2).round(2)
        t['xg_away'] = ((t['away_avg_goals_scored_last_5'] + t['home_avg_goals_conceded_last_5']) / 2).round(2)
        marcadores = [_marcador(a, b, c) for a, b, c in zip(t['xg_home'], t['xg_away'], t['pred_1x2'])]
        t['pred_home_goals'] = [x[0] for x in marcadores]
        t['pred_away_goals'] = [x[1] for x in marcadores]
        t['generated_at'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        t['source'] = 'backtest'
        t['model_version'] = 'backtest'
        filas.append(t[LOG_COLS])

        resumen.append({
            'inicio': inicio, 'matchday': int(test['matchday'].iloc[0]), 'n_train': len(train),
            'n': len(test),
            'aciertos': int((pred == test['y'].values).sum()),
            'log_loss_sum': log_loss(test['y'], p, labels=[0, 1, 2], normalize=False),
        })

    if not filas:
        print("⚠️ No hay datos suficientes para el backtest (baja min_train o añade temporadas).")
        return

    nuevas = pd.concat(filas, ignore_index=True)
    ruta = os.path.join(export_dir, 'prediction_log.csv')
    upsert_log(ruta, nuevas, respetar_live=True)   # nunca pisa predicciones reales

    r = pd.DataFrame(resumen)
    r['accuracy_acum'] = r['aciertos'].cumsum() / r['n'].cumsum()
    r['log_loss_acum'] = r['log_loss_sum'].cumsum() / r['n'].cumsum()
    r.to_csv(os.path.join(export_dir, 'backtest_metrics.csv'), index=False)
    print(r[['matchday', 'n_train', 'n', 'accuracy_acum', 'log_loss_acum']].round(3).to_string(index=False))
    print(f"✅ {len(nuevas)} predicciones de backtest añadidas al registro")


if __name__ == '__main__':
    run_backtest()