#---------------------------FASE 2----------------------------
#En esta fase compramos un armario archivador y pone en 3 cajones etiquetados los esquemas 'raw, staging, marts'

import os #nos ajudara para navegar por el mapa de carpetas del ordenador, sirve para saber en que carpeta estamos parados y crear carpetas nuevas
import duckdb #es el motor de BBDD, crea el archivo de BDD y sabe como almacenar datos en un solo fichero de manera rapida

#Ruta predeterminada para el archivo de la base de datos DuckDB
db_path = os.path.join(os.path.dirname(__file__), '../../data/futbol.duckdb') #__file__: este archivo de codigo en el que estoy parado
                                                                              #os.path.dirname(): signfica que sube un nivel a la carpeta q contiene este archivo
                                    #/data/futbol.duckdb: le dice sal de la carpeta actual, sube 2 niveles y entra en la carpeta data y ahi creara el archivo futbol. duckdb  

def get_db_connection(db_path: str=db_path) -> duckdb.DuckDBPyConnection:
    #Establece y devuelve una conexion a la BBDD DuckDB, crea el directorio si no existe
    os.makedirs(os.path.dirname(db_path), exist_ok=True) #comprueba si la carpeta data existe
    conn = duckdb.connect(db_path) #abre el archivo furbol.duckdb, si no existe duckdb lo creara de nuevo y si ya existe, lo abre para trabajar en el
    return conn #devuelve la conexion q es como dejar la puerta abierta del archivador para meter cosas

#Un esquema en  una BBDD es como una seccion dentro de un archivador. La arquitectura profesional usa medallion
def init_schemas(conn: duckdb.DuckDBPyConnection) -> None:
    #Creamos los esquemas base de la arquitectura medallion (raw, staging, marts)
    schemas = ['raw','staging','marts'] #raw (guardamos la informacin tal cual venga de la API), staging (guardamos los datos tras corregir nombres de equipos repetidos), marts (aqui guardaremos todo lo limpio)
    for schema in schemas:
        conn.execute(f'CREATE SCHEMA IF NOT EXISTS {schema};')
    print('✅ Esquemas inicializados en DuckDB: raw, staging, marts')

if __name__ == '__main__':
    conn = get_db_connection() #abre la conecion y crea el archivo en la carpeta data
    init_schemas(conn) #crea los 3 cajones
    conn.close() #cierra la puerta del archivador