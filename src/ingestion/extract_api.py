#---------------------------FASE 1----------------------------

import os
import json #es un traductor ya q los datos en internet viajan en un formato JSON
import requests #es un navegador online invisible que permite entrar en paginas web
from datetime import datetime #el reloj y calendario para saber que dia es hoy
from dotenv import load_dotenv #es una caja fuerte para guardar contraseñas y calves secretas en un archivo aparte

api_token = 'c37d68aace54498ba38bc07a2677ed3f' #es el 'carnet de identidad' ya que la web exige que uno se identifique

#2. Configuramos los parametros de la API
base_url = 'https://api.football-data.org/v4/competitions/PD/matches' #es la direccion a la que pedimos informacion
headers = {'X-Auth-Token': api_token} #es el sobre donde pegamos la api para que al llegar a la puerta sepan que tienes el permiso

def obtener_y_guardar_partidos(season=2024): #cambiamos el año por si queremos otra temporada
    print(f'Conectando a la API para la temporada {season}')

    respuesta = requests.get(base_url, headers=headers, params={'temporada':season}) #hacemos la peticion a la API: toma la direccion (base_url), muestra el carnet (headers),
                                                                                     #añade la condicion de la temporada (params) y pulsa el boton de buscar (request.get)

    if respuesta.status_code == 200:  #comprobamos que la peticion fue exitosa (codigo 200). En internet responde con numeros de estado: 200 es perfecto, 404 es no encontrado
        data = respuesta.json() #Traduce la respuesta a un texto estructurado en Python
        os.makedirs('data/raw', exist_ok=True) #asi nos aseguramos que la carpeta existe (data/raw), si no la crea automaticamente

        today = datetime.now().strftime("%Y-%m-%d") #generamos el nombre del archivo con la fecha de hoy
        filename = f"data/raw/matches_PD_{season}_{today}.json" #define el nombre exacto con el que vas a bautizar el archivo guardado

        with open(filename, 'w', encoding='utf-8') as file: #guardamos el archivo json.Con el open abrimos o creamos el archivo en modo escritura(w). 
            json.dump(data, file, ensure_ascii=False, indent=4) #con el json.dump: escribe  los datos descargados dentro archivo y con el indent(4)pone espacios para que se pueda leer claramente

        print(f"✅ ¡Éxito! Se han guardado {len(data['matches'])} partidos en: {filename}") #Si todo sale bien, muestra un mensaje indicando cuantos partidos ha encontrado
    else:
        print(f"❌ Error {respuesta.status_code}: {respuesta.text}") #Si el codigo es distinto te avisa que fallo

if __name__ == "__main__":
    obtener_y_guardar_partidos() #Esta es una regla que si ejecutas este archivo desde la terminal, ponte a trabajar en la funcion de inmediato





