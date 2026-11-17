#---------------------------FASE 1----------------------------

import os
import json #es un traductor ya q los datos en internet viajan en un formato JSON
import time #es un cronometro que nos permite hacer pausas cuando la API nos pide esperar
import requests #es un navegador online invisible que permite entrar en paginas web
from datetime import datetime #el reloj y calendario para saber que dia es hoy
from dotenv import load_dotenv #es una caja fuerte para guardar contraseñas y claves secretas en un archivo aparte

load_dotenv() #abre la caja fuerte: lee el archivo .env y deja disponibles las claves que hay dentro (sin esta linea el .env no se lee)

api_token = os.getenv('FOOTBALL_API_TOKEN') #es el 'carnet de identidad': ya no lo escribimos aqui, lo cogemos de la caja fuerte (.env en tu ordenador, o el secreto de GitHub en el servidor)

#2. Configuramos los parametros de la API
base_url = 'https://api.football-data.org/v4/competitions/PD/matches' #es la direccion a la que pedimos informacion
headers = {'X-Auth-Token': api_token} #es el sobre donde pegamos la api para que al llegar a la puerta sepan que tienes el permiso

def temporada_actual(): #calcula sola la temporada en curso, para no tener que cambiar el año a mano cada verano
    hoy = datetime.now() #mira que dia es hoy
    return hoy.year if hoy.month >= 8 else hoy.year - 1 #la temporada empieza en agosto: de agosto a diciembre es el año actual, y de enero a julio es el año anterior

def obtener_y_guardar_partidos(season=None, reintentos=3): #si no le decimos ninguna temporada, usa la actual. Los reintentos son las veces que insiste si la API nos hace esperar
    if not api_token: #comprobamos que el carnet existe antes de salir de casa
        raise RuntimeError('Falta FOOTBALL_API_TOKEN: revisa el archivo .env o el secreto de GitHub') #si no hay carnet, paramos aqui con un aviso claro

    season = season or temporada_actual() #si no nos han dado temporada, ponemos la actual
    print(f'Conectando a la API para la temporada {season}')

    for intento in range(1, reintentos + 1): #repetimos la peticion hasta 3 veces como maximo
        respuesta = requests.get(base_url, headers=headers, params={'season': season}, timeout=30) #hacemos la peticion a la API: toma la direccion (base_url), muestra el carnet (headers),
                                                                                                    #añade la condicion de la temporada (params, que la API llama 'season' y no 'temporada') y pulsa el boton de buscar (requests.get).
                                                                                                    #El timeout es el tiempo maximo de espera: si en 30 segundos no contesta, se corta
        if respuesta.status_code == 200: #comprobamos que la peticion fue exitosa (codigo 200). En internet responde con numeros de estado: 200 es perfecto, 404 es no encontrado
            break #si todo ha ido bien, salimos del bucle y seguimos
        if respuesta.status_code == 429 and intento < reintentos: #el codigo 429 significa que hemos pedido demasiado rapido y la API nos pide esperar
            print('⏳ Limite de peticiones alcanzado. Espero 60 segundos...')
            time.sleep(60) #esperamos un minuto y volvemos a intentarlo
            continue
        raise RuntimeError(f'❌ Error {respuesta.status_code}: {respuesta.text}') #si es otro error, paramos todo y avisamos. Asi el pipeline no sigue adelante con datos viejos sin darnos cuenta

    data = respuesta.json() #Traduce la respuesta a un texto estructurado en Python
    os.makedirs('data/raw', exist_ok=True) #asi nos aseguramos que la carpeta existe (data/raw), si no la crea automaticamente

    filename = f'data/raw/matches_PD_{season}.json' #define el nombre exacto con el que vas a bautizar el archivo guardado. Ya no lleva la fecha: cada vez que se ejecuta se sobrescribe el mismo archivo y no se acumulan copias

    with open(filename, 'w', encoding='utf-8') as file: #guardamos el archivo json. Con el open abrimos o creamos el archivo en modo escritura (w).
        json.dump(data, file, ensure_ascii=False, indent=4) #con el json.dump: escribe los datos descargados dentro del archivo y con el indent(4) pone espacios para que se pueda leer claramente

    jugados = sum(1 for m in data['matches'] if m['status'] == 'FINISHED') #cuenta cuantos partidos ya estan terminados (FINISHED)
    print(f"✅ ¡Éxito! Se han guardado {len(data['matches'])} partidos en: {filename} ({jugados} FINISHED)") #Si todo sale bien, muestra un mensaje indicando cuantos partidos ha encontrado y cuantos estan terminados

def run_extraction(): #es el boton que pulsa main.py para lanzar la descarga completa
    obtener_y_guardar_partidos()

if __name__ == "__main__":
    run_extraction() #Esta es una regla que si ejecutas este archivo desde la terminal, ponte a trabajar en la funcion de inmediato