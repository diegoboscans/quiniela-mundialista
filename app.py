from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import requests

app = Flask(__name__)
# Configuración de CORS para permitir conexiones desde tu frontend en Vercel
CORS(app) 

DB_FILE = 'database.json'
API_TOKEN = 'f5ba1c141b2f495aa7eb896d7d2b4254'

# ==========================================
# RUTAS PRINCIPALES
# ==========================================

@app.route('/')
def home():
    return "El servidor de la Quiniela está funcionando correctamente.", 200

# ==========================================
# FUNCIONES DE BASE DE DATOS
# ==========================================

def cargar_db():
    if not os.path.exists(DB_FILE):
        admin_default = {
            "usuarios": {
                "diegoboscan": {
                    "nombre": "Diego", "apellido": "Boscan", 
                    "username": "diegoboscan", "password": "1234", 
                    "puntos": 0, "pronosticos": {}
                }
            }
        }
        with open(DB_FILE, 'w') as f:
            json.dump(admin_default, f, indent=4)
    
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def guardar_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ==========================================
# MOTOR DE PUNTOS
# ==========================================

def recalcular_ranking_global():
    db = cargar_db()
    usuarios = db.get("usuarios", {})
    try:
        url = "https://api.football-data.org/v4/competitions/WC/matches"
        headers = {"X-Auth-Token": API_TOKEN}
        respuesta = requests.get(url, headers=headers, timeout=10)
        
        if respuesta.status_code == 200:
            partidos = respuesta.json().get("matches", [])
            for username, usuario in usuarios.items():
                puntos_totales = 0
                pronosticos = usuario.get("pronosticos", {})
                for partido in partidos:
                    if partido.get("status") == "FINISHED":
                        score = partido.get("score", {}).get("fullTime", {})
                        real_home = score.get("home")
                        real_away = score.get("away")
                        if real_home is not None and real_away is not None:
                            partido_id = str(partido.get("id"))
                            if partido_id in pronosticos:
                                p_home = pronosticos[partido_id].get("home")
                                p_away = pronosticos[partido_id].get("away")
                                if p_home != "" and p_away != "":
                                    ph, pa = int(p_home), int(p_away)
                                    if ph == real_home and pa == real_away:
                                        puntos_totales += 3
                                    elif ((real_home > real_away and ph > pa) or
                                          (real_away > real_home and pa > ph) or
                                          (real_home == real_away and ph == pa)):
                                        puntos_totales += 1
                usuario["puntos"] = puntos_totales
            guardar_db(db)
    except Exception as e:
        print(f"Error al contrastar resultados con la API: {e}")

# ==========================================
# ENDPOINTS DE LA API
# ==========================================

@app.route('/api/registro', methods=['POST'])
def registrar_usuario():
    datos = request.json
    db = cargar_db()
    username = datos.get('username', '').strip().lower()
    if username in db['usuarios']:
        return jsonify({"success": False, "message": "El usuario ya existe"}), 400
    db['usuarios'][username] = {
        "nombre": datos.get('nombre'), "apellido": datos.get('apellido'),
        "username": username, "password": datos.get('password'),
        "puntos": 0, "pronosticos": {}
    }
    guardar_db(db)
    return jsonify({"success": True, "message": "Usuario registrado con éxito"})

@app.route('/api/login', methods=['POST'])
def login_usuario():
    datos = request.json
    db = cargar_db()
    usuario = db['usuarios'].get(datos.get('username', '').strip().lower())
    if usuario and usuario['password'] == datos.get('password'):
        return jsonify({"success": True, "user": usuario})
    return jsonify({"success": False, "message": "Credenciales incorrectas"}), 401

@app.route('/api/guardar_quiniela', methods=['POST'])
def guardar_quiniela():
    datos = request.json
    db = cargar_db()
    username = datos.get('username', '').strip().lower()
    if username in db['usuarios']:
        db['usuarios'][username]['pronosticos'].update(datos.get('pronosticos', {}))
        guardar_db(db)
        recalcular_ranking_global()
        return jsonify({"success": True, "user": cargar_db()['usuarios'][username]})
    return jsonify({"success": False, "message": "Usuario no encontrado"}), 404

@app.route('/api/ranking', methods=['GET'])
def obtener_ranking():
    recalcular_ranking_global()
    db = cargar_db()
    lista = list(db['usuarios'].values())
    for u in lista: u.pop('password', None)
    return jsonify(lista)

@app.route('/api/recuperar', methods=['POST'])
def recuperar_contrasena():
    datos = request.json
    db = cargar_db()
    username = datos.get('username', '').strip().lower()
    if username in db['usuarios']:
        db['usuarios'][username]['password'] = datos.get('password')
        guardar_db(db)
        return jsonify({"success": True, "message": "Contraseña actualizada"})
    return jsonify({"success": False, "message": "Usuario no existe"}), 404

if __name__ == '__main__':
    # Render asigna el puerto mediante la variable de entorno PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)