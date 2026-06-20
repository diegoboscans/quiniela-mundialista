from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
import os
import requests
import time
import json 

app = Flask(__name__)
CORS(app)

# Configuración de Supabase
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

API_TOKEN = 'f5ba1c141b2f495aa7eb896d7d2b4254' 

MAPA_PAISES = {
    "USA": "us", "United States": "us", "Estados Unidos": "us", "Estados Unidos National Team": "us",
    "Mexico": "mx", "México": "mx", "Mexico National Team": "mx",
    "Canada": "ca", "Canadá": "ca", "Canada National Team": "ca",
    "Argentina": "ar", "Argentina National Team": "ar",
    "Brazil": "br", "Brasil": "br", "Brazil National Team": "br",
    "Uruguay": "uy", "Uruguay National Team": "uy",
    "Colombia": "co", "Colombia National Team": "co",
    "Chile": "cl", "Chile National Team": "cl",
    "Ecuador": "ec", "Ecuador National Team": "ec",
    "Peru": "pe", "Perú": "pe", "Peru National Team": "pe",
    "Paraguay": "py", "Paraguay National Team": "py",
    "Venezuela": "ve", "Venezuela National Team": "ve",
    "Bolivia": "bo", "Bolivia National Team": "bo",
    "Germany": "de", "Alemania": "de", "Germany National Team": "de",
    "France": "fr", "Francia": "fr", "France National Team": "fr",
    "Spain": "es", "España": "es", "Espanha": "es", "Spain National Team": "es",
    "England": "gb", "Inglaterra": "gb", "England National Team": "gb",
    "Italy": "it", "Italia": "it", "Italy National Team": "it",
    "Portugal": "pt", "Portugal National Team": "pt",
    "Netherlands": "nl", "Países Bajos": "nl", "Holanda": "nl", "Netherlands National Team": "nl",
    "Belgium": "be", "Bélgica": "be", "Belgium National Team": "be",
    "Croatia": "hr", "Croacia": "hr", "Croatia National Team": "hr",
    "Switzerland": "ch", "Suiza": "ch", "Switzerland National Team": "ch",
    "Poland": "pl", "Polonia": "pl", "Poland National Team": "pl",
    "Denmark": "dk", "Dinamarca": "dk", "Denmark National Team": "dk",
    "Serbia": "rs", "Serbia National Team": "rs",
    "Austria": "at", "Austria National Team": "at",
    "Sweden": "se", "Suecia": "se", "Sweden National Team": "se",
    "Ukraine": "ua", "Ucrania": "ua", "Ukraine National Team": "ua",
    "Czech Republic": "cz", "República Checa": "cz", "Czech Republic National Team": "cz",
    "Norway": "no", "Noruega": "no", "Norway National Team": "no",
    "Hungary": "hu", "Hungría": "hu", "Hungary National Team": "hu",
    "Greece": "gr", "Grecia": "gr", "Greece National Team": "gr",
    "Turkey": "tr", "Turquía": "tr", "Turkey National Team": "tr",
    "Wales": "gb-wls", "Gales": "gb-wls", "Wales National Team": "gb-wls",
    "Morocco": "ma", "Marruecos": "ma", "Morocco National Team": "ma",
    "Senegal": "sn", "Senegal National Team": "sn",
    "Tunisia": "tn", "Túnez": "tn", "Tunisia National Team": "tn",
    "Cameroon": "cm", "Camerún": "cm", "Cameroon National Team": "cm",
    "Ghana": "gh", "Ghana National Team": "gh",
    "Nigeria": "ng", "Nigeria National Team": "ng",
    "Egypt": "eg", "Egipto": "eg", "Egypt National Team": "eg",
    "Ivory Coast": "ci", "Costa de Marfil": "ci", "Ivory Coast National Team": "ci",
    "Algeria": "dz", "Argelia": "dz", "Algeria National Team": "dz",
    "Japan": "jp", "Japón": "jp", "Japan National Team": "jp",
    "South Korea": "kr", "Corea del Sur": "kr", "South Korea National Team": "kr",
    "Australia": "au", "Australia National Team": "au",
    "Saudi Arabia": "sa", "Arabia Saudita": "sa", "Saudi Arabia National Team": "sa",
    "Iran": "ir", "Irán": "ir", "Iran National Team": "ir",
    "Qatar": "qa", "Qatar National Team": "qa",
    "New Zealand": "nz", "Nueva Zelanda": "nz", "New Zealand National Team": "nz"
}

def obtener_partidos_api():
    CACHE_FILE = 'matches_cache.json'
    if os.path.exists(CACHE_FILE):
        if time.time() - os.path.getmtime(CACHE_FILE) < 3600:
            try:
                with open(CACHE_FILE, 'r') as f: return json.load(f)
            except: pass
    try:
        url = "https://api.football-data.org/v4/competitions/WC/matches"
        headers = {"X-Auth-Token": API_TOKEN}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json().get("matches", [])
            with open(CACHE_FILE, 'w') as f: json.dump(data, f)
            return data
    except: pass
    return []

@app.route('/api/partidos', methods=['GET'])
def endpoint_partidos():
    partidos = obtener_partidos_api()
    for p in partidos:
        p["homeTeam"]["flag"] = MAPA_PAISES.get(p["homeTeam"]["name"], "un")
        p["awayTeam"]["flag"] = MAPA_PAISES.get(p["awayTeam"]["name"], "un")
        p["score_real"] = p.get("score", {}).get("fullTime", {"home": None, "away": None})
    return jsonify(partidos)

def recalcular_y_guardar(username, pronosticos_usuario):
    partidos = obtener_partidos_api()
    puntos = 0
    for partido in partidos:
        if partido.get("status") == "FINISHED":
            pid = str(partido["id"])
            if pid in pronosticos_usuario:
                real = partido["score"]["fullTime"]
                pred = pronosticos_usuario[pid]
                try:
                    ph, pa = int(pred["home"]), int(pred["away"])
                    real_h, real_a = real["home"], real["away"]
                    if real_h is not None and real_a is not None:
                        if ph == real_h and pa == real_a: puntos += 3
                        elif (real_h > real_a and ph > pa) or (real_a > real_h and pa > ph) or (real_h == real_a and ph == pa): puntos += 1
                except: continue
    supabase.table("usuarios").update({"puntos": puntos}).eq("username", username).execute()

@app.route('/api/registro', methods=['POST'])
def registrar_usuario():
    datos = request.json
    try:
        supabase.table("usuarios").insert({
            "username": datos['username'].lower(),
            "nombre": datos['nombre'],
            "password": datos['password'],
            "puntos": 0,
            "pronosticos": {}
        }).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/recuperar', methods=['POST'])
def recuperar_clave():
    datos = request.json
    res = supabase.table("usuarios").update({"password": datos['password']}).eq("nombre", datos['nombre']).execute()
    return jsonify({"success": True})

@app.route('/api/login', methods=['POST'])
def login_usuario():
    datos = request.json
    res = supabase.table("usuarios").select("*").eq("username", datos['username'].lower()).execute()
    user = res.data[0] if res.data else None
    if user and user['password'] == datos['password']:
        return jsonify({"success": True, "user": user})
    return jsonify({"success": False}), 401

@app.route('/api/guardar_quiniela', methods=['POST'])
def guardar_quiniela():
    datos = request.json
    username = datos['username'].lower()
    nuevos = datos['pronosticos']
    res = supabase.table("usuarios").select("pronosticos").eq("username", username).execute()
    if not res.data: return jsonify({"success": False}), 404
    actuales = res.data[0]['pronosticos'] or {}
    for pid, val in nuevos.items():
        if pid not in actuales: actuales[pid] = val
    supabase.table("usuarios").update({"pronosticos": actuales}).eq("username", username).execute()
    recalcular_y_guardar(username, actuales)
    user_final = supabase.table("usuarios").select("*").eq("username", username).execute()
    return jsonify({"success": True, "user": user_final.data[0]})

@app.route('/api/ranking', methods=['GET'])
def obtener_ranking():
    res = supabase.table("usuarios").select("*").execute()
    usuarios = res.data
    for u in usuarios:
        if u.get('pronosticos'): recalcular_y_guardar(u['username'], u['pronosticos'])
    res_final = supabase.table("usuarios").select("username, puntos").order("puntos", desc=True).execute()
    return jsonify(res_final.data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))