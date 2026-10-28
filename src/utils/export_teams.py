import os
import duckdb
import pandas as pd
from src.utils.db import get_db_connection

def export_teams():
    conn = get_db_connection()
    
    # Extraer id y nombre de los equipos locales y visitantes para asegurar la lista completa
    df_teams = conn.execute("""
        SELECT DISTINCT home_team_id AS team_id, home_team_name AS team_name FROM raw.matches_api
        UNION
        SELECT DISTINCT away_team_id AS team_id, away_team_name AS team_name FROM raw.matches_api
        ORDER BY team_name;
    """).df()
    
    conn.close()

    # Generar la URL del escudo (usando los logos PNG de football-data.org)
    df_teams['crest_url'] = df_teams['team_id'].apply(
        lambda tid: f"https://crests.football-data.org/{tid}.png"
    )

    # Crear directorio si no existe y guardar el CSV
    output_dir = os.path.join(os.path.dirname(__file__), '../../data/powerbi')
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, 'dim_teams.csv')
    df_teams.to_csv(output_path, index=False, encoding='utf-8')
    print(f"✅ Exportados {len(df_teams)} equipos a {output_path}")

if __name__ == '__main__':
    export_teams()