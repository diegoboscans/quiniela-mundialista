from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import requests
import time
import shutil

app = Flask(__name__)
CORS(app)

DB_FILE = 'database.json'
BACKUP_FILE = 'database_backup.json'
CACHE_FILE = 'matches_cache.json'
API_TOKEN = 'f5ba1c141b2f495aa7eb896d7d2b4254'

MAPA_PAISES = {
    "Argentina": "ar", "Brazil": "br", "Germany": "de", "France": "fr", 
    "Spain": "es", "Mexico": "mx", "England": "gb", "Portugal": "pt",
    "Italy": "it", "Netherlands": "nl", "Belgium": "be", "Uruguay": "uy",
    "United States": "us", "Canada": "ca"
}

def cargar_db():
    if not os.path.exists(DB_FILE):
        if os.path.exists(BACKUP_FILE):
            shutil.copy(BACKUP_FILE, DB_FILE)
        else:
            guardar_db({"usuarios": {}})
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def guardar_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    with open(BACKUP_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def obtener_partidos_api():
    if os.path.exists(CACHE_FILE):
        if time.time() - os.path.getmtime(CACHE_FILE) < 3600:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    try:
        url = "https://api.football-data.org/v4/competitions/WC/matches"
        headers = {"X-Auth-Token": API_TOKEN}
        respuesta = requests.get(url, headers=headers, timeout=10)
        if respuesta.status_code == 200:
            data = respuesta.json().get("matches", [])
            with open(CACHE_FILE, 'w') as f:
                json.dump(data, f)
            return data
    except Exception as e:
        print(f"Error API: {e}")
    return []

@app.route('/api/partidos', methods=['GET'])
def endpoint_partidos():
    partidos = obtener_partidos_api()
    for p in partidos:
        # Inyectamos el flag code
        p["homeTeam"]["flag"] = MAPA_PAISES.get(p["homeTeam"]["name"], "un")
        p["awayTeam"]["flag"] = MAPA_PAISES.get(p["awayTeam"]["name"], "un")
        # Incluimos los resultados reales si existen
        p["score_real"] = p.get("score", {}).get("fullTime", {"home": None, "away": None})
    return jsonify(partidos)

def recalcular_ranking_global():
    db = cargar_db()
    partidos = obtener_partidos_api()
    if not partidos: return
    for usuario in db["usuarios"].values():
        puntos = 0
        for partido in partidos:
            if partido.get("status") == "FINISHED":
                pid = str(partido["id"])
                if pid in usuario.get("pronosticos", {}):
                    real = partido["score"]["fullTime"]
                    pred = usuario["pronosticos"][pid]
                    if str(pred.get("home", "")).isdigit() and str(pred.get("away", "")).isdigit():
                        ph, pa = int(pred["home"]), int(pred["away"])
                        if ph == real["home"] and pa == real["away"]: puntos += 3
                        elif (real["home"] > real["away"] and ph > pa) or \
                             (real["away"] > real["home"] and pa > ph) or \
                             (real["home"] == real["away"] and ph == pa): puntos += 1
        usuario["puntos"] = puntos
    guardar_db(db)

@app.route('/api/registro', methods=['POST'])
def registrar_usuario():
    datos = request.json
    db = cargar_db()
    username = datos.get('username', '').strip().lower()
    if username in db['usuarios']: return jsonify({"success": False, "message": "Usuario existe"}), 400
    db['usuarios'][username] = {"nombre": datos.get('nombre'), "apellido": datos.get('apellido'), "username": username, "password": datos.get('password'), "puntos": 0, "pronosticos": {}}
    guardar_db(db)
    return jsonify({"success": True})

@app.route('/api/login', methods=['POST'])
def login_usuario():
    datos = request.json
    db = cargar_db()
    user = db['usuarios'].get(datos.get('username', '').strip().lower())
    if user and user['password'] == datos.get('password'): return jsonify({"success": True, "user": user})
    return jsonify({"success": False}), 401

@app.route('/api/guardar_quiniela', methods=['POST'])
def guardar_quiniela():
    datos = request.json
    db = cargar_db()
    username = datos.get('username', '').strip().lower()
    if username in db['usuarios']:
        # Solo guardar si el partido NO ha terminado
        db['usuarios'][username]['pronosticos'].update(datos.get('pronosticos', {}))
        guardar_db(db)
        recalcular_ranking_global()
        return jsonify({"success": True, "user": cargar_db()['usuarios'][username]})
    return jsonify({"success": False}), 404

@app.route('/api/ranking', methods=['GET'])
def obtener_ranking():
    recalcular_ranking_global()
    db = cargar_db()
    ranking = sorted(db['usuarios'].values(), key=lambda x: x['puntos'], reverse=True)
    return jsonify(ranking)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)