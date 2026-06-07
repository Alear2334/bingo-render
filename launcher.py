import webview
import threading
import os
import sys

# Forzar el directorio de trabajo
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Redirigir salidas para que nada se imprima en consola
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')

from app import app 

def run_flask():
    app.run(port=5000, use_reloader=False)

if __name__ == '__main__':
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    window = webview.create_window(
        'Bingo 360 Live', 
        'http://127.0.0.1:5000', 
        width=1200, 
        height=800,
        resizable=True
    )
    
    webview.start()