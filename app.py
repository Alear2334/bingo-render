from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
import os

# --- CONEXIÓN A MONGODB (NUBE) ---
# Aquí pegamos tu URL, asegúrate de que tenga la contraseña '506972' donde dice admin:506972@...
MONGO_URI = "mongodb+srv://admin:506972@cluster0.qcnjhxs.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client['bingo_db']
coleccion = db['registros']

app = Flask(__name__)
app.secret_key = "bingo360_secret_key" 

# --- FUNCIONES DE PERSISTENCIA ---
def cargar_desde_disco():
    # Traemos los datos de la nube
    return list(coleccion.find({}, {'_id': 0}))

def guardar_en_disco(datos):
    # Guardamos en la nube borrando lo anterior para mantener siempre la versión más reciente
    coleccion.delete_many({})
    if datos:
        coleccion.insert_many(datos)

# Cargamos registros al iniciar
registros_control = cargar_desde_disco()
PRECIO_UNITARIO = 500.00

# --- SEGURIDAD ---
@app.before_request
def verificar_login():
    if request.endpoint not in ['login', 'static'] and not session.get('logged_in'):
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Contraseña fija
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

# --- LÓGICA DE PROCESAMIENTO ---
def procesar_matriz_bingo():
    global PRECIO_UNITARIO
    tablas_maestras = {}
    for i in range(1, 501):
        inicio_carton = (i * 6) - 5
        cartones_calculados = [f"{num:03d}" for num in range(inicio_carton, inicio_carton + 6)]
        tablas_maestras[i] = {"nro_tabla": i, "nombre": "", "check": "", "estado": "", "cartones": cartones_calculados}
    
    total_vendidos = 0
    monto_acumulado = 0.0
    
    # Recargamos registros de la nube cada vez que procesamos
    actuales = cargar_desde_disco()
    
    for registro in actuales:
        propietario = registro["nombre"].strip().upper()
        cadena_seleccion = registro["tablas_seleccionadas"]
        status_financiero = registro["estado"]
        
        indices_tablas = [int(p) for p in cadena_seleccion.split(';') if p.strip().isdigit()]
        for nro in indices_tablas:
            if 1 <= nro <= 500:
                total_vendidos += 1
                tablas_maestras[nro].update({"nombre": propietario, "estado": status_financiero, "check": "✓" if status_financiero == "PAGO" else "✕"})
        
        if status_financiero == "PAGO":
            monto_acumulado += (len(indices_tablas) * PRECIO_UNITARIO)

    return tablas_maestras, total_vendidos, monto_acumulado, PRECIO_UNITARIO

# --- RUTAS PRINCIPALES ---
@app.route('/')
def vista_control():
    global registros_control
    registros_control = cargar_desde_disco() # Sincronizar con la nube
    _, vendidos, monto, precio = procesar_matriz_bingo()
    return render_template('control.html', registros=registros_control, total_vendidos=vendidos, monto_total=monto, precio=precio)

@app.route('/guardar_control', methods=['POST'])
def controlador_guardar():
    nombre = request.form.get('nombre', '').strip().upper()
    tablas_sel = request.form.get('tablas_seleccionadas', '').strip()
    estado = request.form.get('estado')
    
    if not tablas_sel.startswith(';'): tablas_sel = f";{tablas_sel}"
    if not tablas_sel.endswith(';'): tablas_sel = f"{tablas_sel};"
    
    indices_nuevos = [int(p) for p in tablas_sel.split(';') if p.strip().isdigit()]
    
    registros_control = cargar_desde_disco()
    tablas_en_uso = []
    for registro in registros_control:
        tablas_en_uso.extend([int(p) for p in registro["tablas_seleccionadas"].split(';') if p.strip().isdigit()])
        
    tablas_ocupadas = [str(nro) for nro in indices_nuevos if nro in tablas_en_uso]
            
    if tablas_ocupadas:
        flash(f"¡Cuidado! Las tablas ya están asignadas: {', '.join(tablas_ocupadas)}", "danger")
    else:
        registros_control.append({"nombre": nombre, "tablas_seleccionadas": tablas_sel, "estado": estado})
        guardar_en_disco(registros_control)
        
    return redirect(url_for('vista_control'))

# ... (El resto de tus rutas de eliminar y cambiar estado se mantienen igual, solo asegúrate de usar cargar_desde_disco() y guardar_en_disco() dentro de ellas)