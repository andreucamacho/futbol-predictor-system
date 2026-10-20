import os
import duckdb
from src.utils.db import get_db_connection

def build_staging_matches(conn: duckdb.DuckDBPyConnection) -> None:
    #Creamos la vista o tabla en staging para unificar y limpiar los partidos de la API
    print("🔄 Limpiando datos en staging.stg_matches...")

    conn.execute("""
        CREATE OR REPLACE TABLE staging.stg_matches AS 
        SELECT
            match_id,
            CAST(utc_date AS TIMESTAMP) AS match_date,
            status,
            matchday,
            stage,
            home_team_id,
            TRIM(home_team_name) AS home_team_name,
            away_team_id,
            TRIM(away_team_name) AS away_team_name,
            score_winner,
            CAST(score_fulltime_home AS INTEGER) AS home_goals,
            CAST(score_fulltime_away AS INTEGER) AS away_goals,
            season_id,
            CASE 
                WHEN score_winner = 'HOME_TEAM' THEN '1'
                WHEN score_winner = 'DRAW' THEN 'X'
                WHEN score_winner = 'AWAY_TEAM' THEN '2'
                ELSE NULL
            END AS result_1x2,
            ingested_at
        FROM raw.matches_api;
    """)
    
    count = conn.execute("SELECT COUNT(*) FROM staging.stg_matches;").fetchone()[0]
    print(f"✅ Capa Staging creada con {count} registros.")

def build_fact_matches(conn: duckdb.DuckDBPyConnection) -> None:
    #Creamos la tabla final fact_matches en el esquema marts

    print("🔄 Generando tabla marts.fact_matches...")
    
    conn.execute("""
        CREATE OR REPLACE TABLE marts.fact_matches AS
        SELECT
            match_id,
            match_date,
            status,
            matchday,
            home_team_id,
            home_team_name,
            away_team_id,
            away_team_name,
            home_goals,
            away_goals,
            result_1x2
        FROM staging.stg_matches
        ORDER BY match_date ASC;
    """)
    
    count = conn.execute("SELECT COUNT(*) FROM marts.fact_matches;").fetchone()[0]
    print(f"✅ Capa Marts (fact_matches) creada con {count} registros.")

def run_transformations():
    conn = get_db_connection()
    build_staging_matches(conn)
    build_fact_matches(conn)
    conn.close

if __name__ == '__main__':
    run_transformations()