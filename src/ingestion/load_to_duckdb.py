import os
import glob
import json
import pandas as pd
import duckdb
from src.utils.db import get_db_connection, init_schemas

raw_data_dir = os.path.join(os.path.dirname(__file__), '../../data/raw')

def load_json_matches_to_raw(conn: duckdb.DuckDBPyConnection) -> None:
    json_pattern = os.path.join(raw_data_dir, 'matches_PD_*.json')
    json_files = glob.glob(json_pattern)

    if not json_files:
        print("⚠️ No se encontraron archivos JSON de partidos en data/raw/")
        return
    print(f"📁 Se encontraron {len(json_files)} archivo(s) JSON para procesar.")

    records = []
    for file_path in json_files:
        print(f"🔄 Leyendo {os.path.basename(file_path)}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for m in data.get('matches', []):
            records.append({
                'match_id': m.get('id'),
                'utc_date': m.get('utcDate'),
                'status': m.get('status'),
                'matchday': m.get('matchday'),
                'stage': m.get('stage'),
                'home_team_id': m.get('homeTeam', {}).get('id'),
                'home_team_name': m.get('homeTeam', {}).get('name'),
                'away_team_id': m.get('awayTeam', {}).get('id'),
                'away_team_name': m.get('awayTeam', {}).get('name'),
                'score_winner': m.get('score', {}).get('winner'),
                'score_fulltime_home': m.get('score', {}).get('fullTime', {}).get('home'),
                'score_fulltime_away': m.get('score', {}).get('fullTime', {}).get('away'),
                'season_id': m.get('season', {}).get('id'),
                'season_start_date': m.get('season', {}).get('startDate'),
                'season_end_date': m.get('season', {}).get('endDate')
            })

    if not records:
        print("⚠️ No se extrajeron registros de los JSON.")
        return

    # Convertimos los datos a un DataFrame de pandas
    df_matches = pd.DataFrame(records)

    # 1. Crear tabla en DuckDB si no existe
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw.matches_api (
            match_id BIGINT,
            utc_date VARCHAR,
            status VARCHAR,
            matchday INT,
            stage VARCHAR,
            home_team_id BIGINT,
            home_team_name VARCHAR,
            away_team_id BIGINT,
            away_team_name VARCHAR,
            score_winner VARCHAR,
            score_fulltime_home INT,
            score_fulltime_away INT,
            season_id BIGINT,
            season_start_date VARCHAR,
            season_end_date VARCHAR,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Carga idempotente: Insertar solo los partidos que no existen aún en DuckDB
    conn.execute("""
        INSERT INTO raw.matches_api (
            match_id, utc_date, status, matchday, stage, 
            home_team_id, home_team_name, away_team_id, away_team_name, 
            score_winner, score_fulltime_home, score_fulltime_away, 
            season_id, season_start_date, season_end_date
        )
        SELECT 
            match_id, utc_date, status, matchday, stage, 
            home_team_id, home_team_name, away_team_id, away_team_name, 
            score_winner, score_fulltime_home, score_fulltime_away, 
            season_id, season_start_date, season_end_date
        FROM df_matches
        WHERE match_id NOT IN (SELECT match_id FROM raw.matches_api);
    """)

    count = conn.execute("SELECT COUNT(*) FROM raw.matches_api;").fetchone()[0]
    print(f"✅ Carga completada. Total de registros en raw.matches_api: {count}")

def load_csv_matches_to_raw(conn: duckdb.DuckDBPyConnection) -> None:
    csv_pattern = os.path.join(raw_data_dir, '*.csv')
    csv_files = glob.glob(csv_pattern)

    if not csv_files:
        print("ℹ️ No hay archivos CSV en data/raw/ aún. Se omitirá raw.matches_csv por ahora.")
        return

    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw.matches_csv AS 
        SELECT *, CURRENT_TIMESTAMP AS ingested_at 
        FROM read_csv_auto(?, union_by_name=True);
    """, [csv_pattern])

    count = conn.execute("SELECT COUNT(*) FROM raw.matches_csv;").fetchone()[0]
    print(f"✅ Carga completada. Total de registros en raw.matches_csv: {count}")

def run_ingestion():
    conn = get_db_connection()
    init_schemas(conn)
    load_json_matches_to_raw(conn)
    load_csv_matches_to_raw(conn)
    conn.close()

if __name__ == '__main__':
    run_ingestion()

#Este codigo funciona como un puente que traslada toda la informacion suelta descargada desde internet hacia la BBDD de DuckDB. Explota la carpeta de datos crudos
#para identificar cualquier archivo descargado, ya provenga de las llamadas de API en JSON o CSV. Una vez localizadas, abre la conexion, asegura existencia del primer nivel de
#almacenamiento llamado esquema raw y analiza la estructura interna de los documentos sin modificar el contenido original. 
#Traduce la informacion empaquetada en una tabla llamada matches_api, abstrayendo datos clave. Aplica una regla de carga limpia q verifica el identificador de cada partido
#antes de guardarlo, asegurando q solo se añadan aquellos encuentros q no se hayan registrado con anterioridad. Tras repetir un proceso similar con los ficheros CSV, la funcion
#contabiliza los registros almacenados, emite un informe con el total de los partidos guardado y cierra la conexion de la BBDD para dejar los datos listos para la siguiente fase. 