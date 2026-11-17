import sys
import os
import argparse
import subprocess
import time

from src.ingestion.extract_api import obtener_y_guardar_partidos
from src.utils.db import get_db_connection, init_schemas
from src.ingestion.load_to_duckdb import run_ingestion
from src.features.transform_data import run_transformations
from src.features.build_features import run_feature_engineering
from src.models.evaluate_models import run_model_benchmark
from src.models.predict import predict_upcoming_matches
from src.utils.export_for_powerbi import export_data_for_powerbi

def ejecutar(nombre, funcion):
    print(f"--- {nombre} ---")
    inicio = time.time()
    funcion()
    print(f"⏱️ {time.time() - inicio:.1f} s\n")


def subir_a_github():
    print("--- SUBIDA A GITHUB ---")
    subprocess.run(["git", "add", "-f", "data/powerbi"], check=True)
    # check=False: si no hay cambios, commit devuelve error y no es grave
    subprocess.run(["git", "commit", "-m", "actualiza datos y predicciones"], check=False)
    subprocess.run(["git", "push"], check=True)
    print("✅ Datos subidos\n")

def run_full_pipeline(skip_extract=False, train=False, push=False):
    print("🚀 INICIANDO PIPELINE END-TO-END DE PREDICCIÓN DE FÚTBOL 🚀\n")

    if not skip_extract:
        ejecutar("[1] EXTRACCIÓN DESDE LA API", obtener_y_guardar_partidos)
    ejecutar("[2] INGESTA A DUCKDB", run_ingestion)
    ejecutar("[3] LIMPIEZA Y STAGING", run_transformations)
    ejecutar("[4] FEATURE ENGINEERING", run_feature_engineering)

    if train:
        ejecutar("[5] ENTRENAMIENTO Y BENCHMARK", run_model_benchmark)
    else:
        print("--- [5] ENTRENAMIENTO omitido (usa --train para reentrenar) ---\n")

    ejecutar("[6] PREDICCIONES", predict_upcoming_matches)
    ejecutar("[7] EXPORTACIÓN PARA POWER BI", export_data_for_powerbi)

    if push:
        subir_a_github()

    print("🎉 PIPELINE EJECUTADO CON ÉXITO 🎉")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Pipeline de predicción de fútbol")
    parser.add_argument("--skip-extract", action="store_true",
                        help="No descargar de la API (usa los JSON ya guardados)")
    parser.add_argument("--train", action="store_true",
                        help="Reentrenar y comparar modelos")
    parser.add_argument("--push", action="store_true",
                        help="Subir data/powerbi a GitHub al terminar")
    args = parser.parse_args()

    run_full_pipeline(args.skip_extract, args.train, args.push)