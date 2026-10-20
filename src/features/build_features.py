import duckdb
from src.utils.db import get_db_connection

def build_team_features(conn: duckdb.DuckDBPyConnection) -> None:
    #Calculamos la forma reciente y promedios de goles de los ultimos 5 partidos para cada equipo sin data leakage
    #Llamamos a la funcion get_db_connection() q ya habiamos creado para abrir la puerta de entrada al archivo futbol.duckdb y poder trabajar dentro de el
    print("🔄 Calculando features avanzadas (últimos 5 partidos)...")

    conn.execute("""
        CREATE OR REPLACE TABLE marts.fact_features AS
        WITH team_matches AS (
            -- Descomponemos cada partido en 2 filas: una para el local y otra para el visitante
            SELECT
                match_id,
                match_date,
                home_team_id AS team_id,
                home_team_name AS team_name,
                home_goals AS goals_scored,
                away_goals AS goals_conceded,
                CASE 
                    WHEN result_1x2 = '1' THEN 3
                    WHEN result_1x2 = 'X' THEN 1
                    ELSE 0
                END AS points
            FROM marts.fact_matches
            WHERE status = 'FINISHED'

            UNION ALL

            SELECT
                match_id,
                match_date,
                away_team_id AS team_id,
                away_team_name AS team_name,
                away_goals AS goals_scored,
                home_goals AS goals_conceded,
                CASE 
                    WHEN result_1x2 = '2' THEN 3
                    WHEN result_1x2 = 'X' THEN 1
                    ELSE 0
                END AS points
            FROM marts.fact_matches
            WHERE status = 'FINISHED'
        ),
        
        rolling_metrics AS (
            -- Calculamos métricas de los últimos 5 partidos usando Window Functions (excluyendo el partido actual)
            SELECT
                match_id,
                team_id,
                match_date,
                SUM(points) OVER (
                    PARTITION BY team_id 
                    ORDER BY match_date 
                    ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
                ) AS points_last_5,
                AVG(goals_scored) OVER (
                    PARTITION BY team_id 
                    ORDER BY match_date 
                    ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
                ) AS avg_goals_scored_last_5,
                AVG(goals_conceded) OVER (
                    PARTITION BY team_id 
                    ORDER BY match_date 
                    ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
                ) AS avg_goals_conceded_last_5
            FROM team_matches
        )

        -- Unimos las métricas calculadas con la tabla principal fact_matches
        SELECT
            m.match_id,
            m.match_date,
            m.matchday,
            m.home_team_name,
            m.away_team_name,
            -- Features del equipo local
            COALESCE(h.points_last_5, 0) AS home_points_last_5,
            COALESCE(ROUND(h.avg_goals_scored_last_5, 2), 0.0) AS home_avg_goals_scored_last_5,
            COALESCE(ROUND(h.avg_goals_conceded_last_5, 2), 0.0) AS home_avg_goals_conceded_last_5,
            -- Features del equipo visitante
            COALESCE(a.points_last_5, 0) AS away_points_last_5,
            COALESCE(ROUND(a.avg_goals_scored_last_5, 2), 0.0) AS away_avg_goals_scored_last_5,
            COALESCE(ROUND(a.avg_goals_conceded_last_5, 2), 0.0) AS away_avg_goals_conceded_last_5,
            -- Target / Objetivo
            m.result_1x2
        FROM marts.fact_matches m
        LEFT JOIN rolling_metrics h 
            ON m.match_id = h.match_id AND m.home_team_id = h.team_id
        LEFT JOIN rolling_metrics a 
            ON m.match_id = a.match_id AND m.away_team_id = a.team_id
        WHERE m.status = 'FINISHED'
        ORDER BY m.match_date ASC;
    """)

    count = conn.execute("SELECT COUNT(*) FROM marts.fact_features;").fetchone()[0]
    print(f"✅ Tabla marts.fact_features creada con {count} filas y métricas calculadas.")

#Ahora, con el siguiente codigo, abrimos la conexion con DuckDB, ejecuta el calculo descrito de las variables, imprime la confirmacion en la terminal y cierra la BBDD
def run_feature_engineering():
    conn = get_db_connection()
    build_team_features(conn)
    conn.close()

if __name__ == '__main__':
    run_feature_engineering()