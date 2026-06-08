from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
import os

app = Flask(__name__)
app.secret_key = "bingo360_secret_key" 

# --- CONEXIÓN A MONGODB ATLAS ---
MONGO_URI = "mongodb+srv://admin:506972@cluster0.qcnjhxs.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client['bingo_db']
coleccion = db['registros']

# --- FUNCIONES DE PERSISTENCIA EN LA NUBE ---
def cargar_registros():
    return list(coleccion.find({}, {'_id': 0}))

def guardar_registros(datos):
    coleccion.delete_many({})
    if datos:
        coleccion.insert_many(datos)

PRECIO_UNITARIO = 500.00

# --- SEGURIDAD ---
@app.before_request
def verificar_login():
    if request.endpoint not in ['login', 'static'] and not session.get('logged_in'):
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('usuario') == "admin" and request.form.get('clave') == "506972":
            session['logged_in'] = True
            return redirect(url_for('vista_control'))
        flash("Usuario o clave incorrectos")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# --- LÓGICA ---
def procesar_matriz_bingo():
    global PRECIO_UNITARIO
    tablas_maestras = {}
    for i in range(1, 501):
        inicio_carton = (i * 6) - 5
        cartones_calc = [f"{num:03d}" for num in range(inicio_carton, inicio_carton + 6)]
        tablas_maestras[i] = {"nro_tabla": i, "nombre": "", "check": "", "estado": "", "cartones": cartones_calc}
    
    total_vendidos = 0
    monto_acumulado = 0.0
    registros = cargar_registros()
    
    for registro in registros:
        indices = [int(p) for p in registro["tablas_seleccionadas"].split(';') if p.strip().isdigit()]
        status = registro["estado"]
        for nro in indices:
            if 1 <= nro <= 500:
                total_vendidos += 1
                tablas_maestras[nro].update({"nombre": registro["nombre"], "estado": status, "check": "✓" if status == "PAGO" else "✕"})
        if status == "PAGO":
            monto_acumulado += (len(indices) * PRECIO_UNITARIO)
    return tablas_maestras, total_vendidos, monto_acumulado, PRECIO_UNITARIO

@app.route('/')
def vista_control():
    registros = cargar_registros()
    _, vendidos, monto, precio = procesar_matriz_bingo()
    return render_template('control.html', registros=registros, total_vendidos=vendidos, monto_total=monto, precio=precio)

# --- NUEVO AJUSTE: RUTA PARA ACTUALIZAR PRECIO ---
@app.route('/actualizar_precio', methods=['POST'])
def controlador_actualizar_precio():
    global PRECIO_UNITARIO
    nuevo_precio = request.form.get('nuevo_precio')
    if nuevo_precio:
        PRECIO_UNITARIO = float(nuevo_precio)
    return redirect(url_for('vista_control'))

@app.route('/guardar_control', methods=['POST'])
def controlador_guardar():
    registros = cargar_registros()
    nombre = request.form.get('nombre', '').strip().upper()
    tablas_sel = request.form.get('tablas_seleccionadas', '').strip()
    estado = request.form.get('estado')
    
    if not tablas_sel.startswith(';'): tablas_sel = f";{tablas_sel}"
    if not tablas_sel.endswith(';'): tablas_sel = f"{tablas_sel};"
    
    registros.append({"nombre": nombre, "tablas_seleccionadas": tablas_sel, "estado": estado})
    guardar_registros(registros)
    return redirect(url_for('vista_control'))

@app.route('/cambiar_estado/<int:index>', methods=['POST'])
def controlador_cambiar_estado(index):
    registros = cargar_registros()
    registros[index]['estado'] = request.form.get('nuevo_estado')
    guardar_registros(registros)
    return redirect(url_for('vista_control'))

@app.route('/eliminar_control/<int:index>')
def controlador_eliminar(index):
    registros = cargar_registros()
    registros.pop(index)
    guardar_registros(registros)
    return redirect(url_for('vista_control'))

@app.route('/borrar_todo')
def controlador_borrar_todo():
    guardar_registros([])
    return redirect(url_for('vista_control'))

@app.route('/listado')
def vista_listado():
    tablas, _, _, _ = procesar_matriz_bingo()
    return render_template('listado.html', tablas=tablas)

@app.route('/disponible')
def vista_disponibilidad():
    tablas, _, _, _ = procesar_matriz_bingo()
    matriz_render = []
    for r in range(1, 101):
        fila_bloque = {
            "b1_nro": r,     "b1_name": tablas[r]["nombre"],     "b1_chk": tablas[r]["check"],
            "b2_nro": r+100, "b2_name": tablas[r+100]["nombre"], "b2_chk": tablas[r+100]["check"],
            "b3_nro": r+200, "b3_name": tablas[r+200]["nombre"], "b3_chk": tablas[r+200]["check"],
            "b4_nro": r+300, "b4_name": tablas[r+300]["nombre"], "b4_chk": tablas[r+300]["check"],
            "b5_nro": r+400, "b5_name": tablas[r+400]["nombre"], "b5_chk": tablas[r+400]["check"]
        }
        matriz_render.append(fila_bloque)
    return render_template('disponible.html', bloques=matriz_render)

if __name__ == '__main__':
    app.run()