import sys
import os

from src.utils.db import get_db_connection, init_schemas
from src.ingestion.load_to_duckdb import run_ingestion
from src.features.transform_data import run_transformations
from src.features.build_features import run_feature_engineering
from src.models.evaluate_models import run_model_benchmark
from src.models.predict import predict_upcoming_matches

def run_full_pipeline():
    print("🚀 INICIANDO PIPELINE END-TO-END DE PREDICCIÓN DE FÚTBOL 🚀\n")
    
    print("--- [1/5] FASE 2: INGESTA DE DATOS A DUCKDB ---")
    run_ingestion()
    print("\n")

    print("--- [2/5] FASE 3A: LIMPIEZA Y STAGING ---")
    run_transformations()
    print("\n")

    print("--- [3/5] FASE 3B: FEATURE ENGINEERING ---")
    run_feature_engineering()
    print("\n")

    print("--- [4/5] FASE 4/5: ENTRENAMIENTO Y BENCHMARK DE MODELOS ---")
    run_model_benchmark()
    print("\n")

    print("--- [5/5] GENERACIÓN DE PREDICCIONES ---")
    predict_upcoming_matches()
    print("\n")

    print("🎉 PIPELINE EJECUTADO CON ÉXITO AL 100% 🎉")

if __name__ == '__main__':
    run_full_pipeline()