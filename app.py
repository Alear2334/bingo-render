from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os

# --- AJUSTE DE RUTAS ---
# Esto garantiza que los archivos siempre se guarden en la misma carpeta que el script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_DATA = os.path.join(BASE_DIR, 'data_bingo.json')
ARCHIVO_CONFIG = os.path.join(BASE_DIR, 'config.json')

app = Flask(__name__)
app.secret_key = "bingo360_secret_key" 

# --- FUNCIONES DE PERSISTENCIA Y CONFIG ---
def cargar_config():
    # Intentamos cargar el archivo si existe
    if os.path.exists(ARCHIVO_CONFIG):
        try:
            with open(ARCHIVO_CONFIG, 'r') as f: 
                return json.load(f)
        except Exception:
            pass
    # Si falla la lectura o el archivo no está, devolvemos tu contraseña deseada
    return {"usuario": "admin", "clave": "506972"}

def cargar_desde_disco():
    if os.path.exists(ARCHIVO_DATA):
        with open(ARCHIVO_DATA, 'r') as f: return json.load(f)
    return []

def guardar_en_disco(datos):
    with open(ARCHIVO_DATA, 'w') as f: json.dump(datos, f, indent=4)

registros_control = cargar_desde_disco()
PRECIO_UNITARIO = 500.00

# --- SEGURIDAD ---
@app.before_request
def verificar_login():
    if request.endpoint not in ['login', 'static'] and not session.get('logged_in'):
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    config = cargar_config()
    if request.method == 'POST':
        if request.form.get('usuario') == config['usuario'] and request.form.get('clave') == config['clave']:
            session['logged_in'] = True
            return redirect(url_for('vista_control'))
        flash("Usuario o clave incorrectos")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/editar_credenciales', methods=['POST'])
def editar_credenciales():
    with open(ARCHIVO_CONFIG, 'w') as f:
        json.dump({"usuario": request.form['usuario'], "clave": request.form['clave']}, f)
    flash("Credenciales actualizadas correctamente")
    return redirect(url_for('vista_control'))

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
    
    for registro in registros_control:
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
    _, vendidos, monto, precio = procesar_matriz_bingo()
    return render_template('control.html', registros=registros_control, total_vendidos=vendidos, monto_total=monto, precio=precio)

@app.route('/actualizar_precio', methods=['POST'])
def controlador_actualizar_precio():
    global PRECIO_UNITARIO
    nuevo_precio = request.form.get('nuevo_precio', 0)
    PRECIO_UNITARIO = float(nuevo_precio)
    return redirect(url_for('vista_control'))

@app.route('/guardar_control', methods=['POST'])
def controlador_guardar():
    nombre = request.form.get('nombre', '').strip().upper()
    tablas_sel = request.form.get('tablas_seleccionadas', '').strip()
    estado = request.form.get('estado')
    
    if not tablas_sel.startswith(';'): tablas_sel = f";{tablas_sel}"
    if not tablas_sel.endswith(';'): tablas_sel = f"{tablas_sel};"
    
    indices_nuevos = [int(p) for p in tablas_sel.split(';') if p.strip().isdigit()]
    
    tablas_ocupadas = []
    tablas_en_uso = []
    for registro in registros_control:
        tablas_en_uso.extend([int(p) for p in registro["tablas_seleccionadas"].split(';') if p.strip().isdigit()])
        
    for nro in indices_nuevos:
        if nro in tablas_en_uso:
            tablas_ocupadas.append(str(nro))
            
    if tablas_ocupadas:
        flash(f"¡Cuidado! Las tablas ya están asignadas: {', '.join(tablas_ocupadas)}", "danger")
    else:
        registros_control.append({"nombre": nombre, "tablas_seleccionadas": tablas_sel, "estado": estado})
        guardar_en_disco(registros_control)
        
    return redirect(url_for('vista_control'))

@app.route('/cambiar_estado/<int:index>', methods=['POST'])
def controlador_cambiar_estado(index):
    registros_control[index]['estado'] = request.form.get('nuevo_estado')
    guardar_en_disco(registros_control)
    return redirect(url_for('vista_control'))

@app.route('/eliminar_control/<int:index>')
def controlador_eliminar(index):
    registros_control.pop(index)
    guardar_en_disco(registros_control)
    return redirect(url_for('vista_control'))

@app.route('/borrar_todo')
def controlador_borrar_todo():
    registros_control.clear()
    guardar_en_disco(registros_control)
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