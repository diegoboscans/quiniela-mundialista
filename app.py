from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import requests

app = Flask(__name__)
CORS(app)

DB_FILE = 'database.json'
API_TOKEN = 'f5ba1c141b2f495aa7eb896d7d2b4254'

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
# MOTOR DE COMPARACIÓN DE MARCADORES Y PUNTOS
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
                                    ph = int(p_home)
                                    pa = int(p_away)

                                    # Comparación exacta -> 3 pts
                                    if ph == real_home and pa == real_away:
                                        puntos_totales += 3
                                    # Comparación de tendencia (Ganador/Empate) -> 1 pt
                                    elif (
                                        (real_home > real_away and ph > pa) or
                                        (real_away > real_home and pa > ph) or
                                        (real_home == real_away and ph == pa)
                                    ):
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
        "nombre": datos.get('nombre'),
        "apellido": datos.get('apellido'),
        "username": username,
        "password": datos.get('password'),
        "puntos": 0,
        "pronosticos": {}
    }
    guardar_db(db)
    return jsonify({"success": True, "message": "Usuario registrado con éxito"})

@app.route('/api/login', methods=['POST'])
def login_usuario():
    datos = request.json
    db = cargar_db()
    username = datos.get('username', '').strip().lower()
    password = datos.get('password')

    usuario = db['usuarios'].get(username)
    if usuario and usuario['password'] == password:
        return jsonify({"success": True, "user": usuario})
    
    return jsonify({"success": False, "message": "Credenciales incorrectas"}), 401

@app.route('/api/guardar_quiniela', methods=['POST'])
def guardar_quiniela():
    datos = request.json
    db = cargar_db()
    username = datos.get('username', '').strip().lower()
    nuevos_pronosticos = datos.get('pronosticos', {})

    if username in db['usuarios']:
        # Guardar marcadores
        db['usuarios'][username]['pronosticos'].update(nuevos_pronosticos)
        guardar_db(db)
        
        # Comparar inmediatamente con los resultados reales
        recalcular_ranking_global()
        
        # Recargar el usuario con sus puntos actualizados antes de responder
        db_actualizada = cargar_db()
        return jsonify({"success": True, "user": db_actualizada['usuarios'][username]})
    
    return jsonify({"success": False, "message": "Usuario no encontrado"}), 404

@app.route('/api/ranking', methods=['GET'])
def obtener_ranking():
    recalcular_ranking_global()
    db = cargar_db()
    lista_usuarios = list(db['usuarios'].values())
    for u in lista_usuarios:
        u.pop('password', None)
    return jsonify(lista_usuarios)

@app.route('/api/recuperar', methods=['POST'])
def recuperar_contrasena():
    datos = request.json
    db = cargar_db()
    username = datos.get('username', '').strip().lower()
    nueva_password = datos.get('password')

    # Verificar si el usuario existe en nuestra base de datos json
    if username in db['usuarios']:
        # Actualizar la contraseña con la nueva ingresada
        db['usuarios'][username]['password'] = nueva_password
        guardar_db(db)
        return jsonify({"success": True, "message": "Contraseña actualizada correctamente"})
    
    return jsonify({"success": False, "message": "El nombre de usuario no existe"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)