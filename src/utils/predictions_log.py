import os
import numpy as np
import pandas as pd

PRED_COLS = ['pred_1x2', 'prob_1', 'prob_X', 'prob_2',
             'xg_home', 'xg_away', 'pred_home_goals', 'pred_away_goals']
META_COLS = ['generated_at', 'source', 'model_version']
LOG_COLS = ['match_id', 'matchday', 'match_date'] + PRED_COLS + META_COLS
NUMERICAS = ['prob_1', 'prob_X', 'prob_2', 'xg_home', 'xg_away',
             'pred_home_goals', 'pred_away_goals']


def leer_log(ruta):
    if os.path.exists(ruta):
        log = pd.read_csv(ruta)
    else:
        log = pd.DataFrame(columns=LOG_COLS)
    log['match_date'] = pd.to_datetime(log['match_date'])
    return log


def upsert_log(ruta, nuevas, respetar_live=False):
    log = leer_log(ruta)
    nuevas = nuevas.copy()
    nuevas['match_date'] = pd.to_datetime(nuevas['match_date'])

    if respetar_live:
        live = set(log.loc[log['source'] == 'live', 'match_id'])
        nuevas = nuevas[~nuevas['match_id'].isin(live)]

    log = log[~log['match_id'].isin(nuevas['match_id'])]
    partes = [p for p in (log, nuevas[LOG_COLS]) if len(p)]
    log = pd.concat(partes, ignore_index=True) if partes else nuevas[LOG_COLS]
    log['match_date'] = pd.to_datetime(log['match_date'])
    log.sort_values('match_date').to_csv(ruta, index=False)
    return log


def aplicar_log(df, ruta, version):
    """Guarda las predicciones de partidos futuros y sustituye las de los
    partidos ya empezados por las que se hicieron ANTES de jugarse."""
    ahora = pd.Timestamp.now(tz='UTC').tz_localize(None)
    df = df.copy()
    df['match_date'] = pd.to_datetime(df['match_date'])
    marca = ahora.strftime('%Y-%m-%d %H:%M:%S')

    futuro_pend = (df['match_date'] > ahora) & df['result_1x2'].isna()
    con_pred = futuro_pend & df['pred_1x2'].notna()

    nuevas = df.loc[con_pred, ['match_id', 'matchday', 'match_date'] + PRED_COLS].copy()
    nuevas['generated_at'] = marca
    nuevas['source'] = 'live'
    nuevas['model_version'] = version
    log = upsert_log(ruta, nuevas) if len(nuevas) else leer_log(ruta)

    idx = log.drop_duplicates('match_id', keep='last').set_index('match_id')
    for c in PRED_COLS + META_COLS:
        if c not in df.columns:
            df[c] = np.nan
        df[c] = df[c].astype(object)
    congelado = ~futuro_pend
    for c in PRED_COLS + META_COLS:
        df.loc[congelado, c] = df.loc[congelado, 'match_id'].map(idx[c])
    df.loc[con_pred, 'generated_at'] = marca
    df.loc[con_pred, 'source'] = 'live'
    df.loc[con_pred, 'model_version'] = version
    for c in NUMERICAS:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df