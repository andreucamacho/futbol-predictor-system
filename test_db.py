import duckdb

con = duckdb.connect("data/futbol.duckdb")

print("--- ÚLTIMOS PARTIDOS FINALIZADOS EN DUCKDB ---")
df_finished = con.execute("""
    SELECT match_id, utc_date, status, matchday, score_fulltime_home, score_fulltime_away 
    FROM raw.matches_api 
    WHERE status = 'FINISHED' 
    ORDER BY utc_date DESC 
    LIMIT 5
""").df()

print(df_finished)

print("\n--- ARCHIVOS JSON DISPONIBLES EN RAW ---")
import glob
print(glob.glob("data/raw/*.json"))