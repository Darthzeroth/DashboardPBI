import os
import requests
import msal
from flask import Flask, render_template, redirect, url_for
from dotenv import load_dotenv
import json # <-- Nueva importación

load_dotenv()

app = Flask(__name__)

# --- CREDENCIALES ---
CLIENT_ID = os.getenv('CLIENT_ID')
TENANT_ID = os.getenv('TENANT_ID')
PBI_USER = os.getenv('PBI_USER')
PBI_PASSWORD = os.getenv('PBI_PASSWORD')
AUTHORITY_URL = f'https://login.microsoftonline.com/{TENANT_ID}'
SCOPE = ["https://analysis.windows.net/powerbi/api/Report.Read.All"]

# --- CONFIGURACIÓN DEL CATÁLOGO DE REPORTES ---
# --- CARGAR CATÁLOGO DE REPORTES DESDE JSON ---
# Leemos el archivo y lo convertimos en una lista de Python automáticamente
try:
    with open('reportes.json', 'r', encoding='utf-8') as archivo:
        MIS_REPORTES = json.load(archivo)
except FileNotFoundError:
    print("⚠️ Error: No se encontró el archivo reportes.json")
    MIS_REPORTES = []
except json.JSONDecodeError:
    print("⚠️ Error: El archivo reportes.json tiene un error de formato")
    MIS_REPORTES = []


# --- INICIALIZAR MSAL GLOBALMENTE ---
# Al dejarlo aquí afuera, su memoria (caché) persiste mientras Flask esté corriendo
app_msal = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY_URL)
def get_access_token():
    # 1. Buscamos si la cuenta ya existe en la memoria de MSAL
    cuentas = app_msal.get_accounts(username=PBI_USER)
    
    if cuentas:
        # Intentamos obtener el token silenciosamente (desde la caché)
        result = app_msal.acquire_token_silent(SCOPE, account=cuentas[0])
        if result and "access_token" in result:
            print("⚡ Token rápido obtenido desde la memoria caché")
            return result['access_token'], None

    # 2. Si no hay cuenta en caché o el token caducó, vamos a Azure
    print("☁️ Solicitando nuevo token a Azure...")
    result = app_msal.acquire_token_by_username_password(PBI_USER, PBI_PASSWORD, scopes=SCOPE)
    
    if "access_token" in result:
        return result['access_token'], None
    else:
        error_msg = f"Error: {result.get('error')} | Descripción: {result.get('error_description')}"
        return None, error_msg

# Ahora la función recibe IDs dinámicos
def get_report_details(token, group_id, report_id):
    headers = {'Authorization': f'Bearer {token}'}
    api_url = f'https://api.powerbi.com/v1.0/myorg/groups/{group_id}/reports/{report_id}'
    response = requests.get(api_url, headers=headers)
    return response.json() if response.status_code == 200 else None

@app.route('/')
def home():
    # Redirigir siempre al primer reporte (índice 0)
    return redirect(url_for('ver_reporte', indice=0))

@app.route('/reporte/<int:indice>')
def ver_reporte(indice):
    if indice < 0 or indice >= len(MIS_REPORTES):
        return "Reporte no encontrado", 404

    # Recibimos tanto el token como el posible error
    token, error_msal = get_access_token()
    
    if not token: 
        # Mostramos el error directo en la página web con estilo básico
        return f"""
        <div style='font-family: sans-serif; padding: 20px; color: #721c24; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px;'>
            <h2>Error de Autenticación con Azure</h2>
            <p><b>Detalle técnico:</b> {error_msal}</p>
        </div>
        """, 401

    reporte_seleccionado = MIS_REPORTES[indice]
    datos_pbi = get_report_details(token, reporte_seleccionado['group_id'], reporte_seleccionado['report_id'])
    
    if not datos_pbi: return "Error cargando reporte de Power BI", 500

    return render_template(
        'index.html',
        menu=MIS_REPORTES,
        activo=indice,
        access_token=token,
        embed_url=datos_pbi['embedUrl'],
        report_id=datos_pbi['id']
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    #app.run(host="0.0.0.0", debug=True, port=5000)
    