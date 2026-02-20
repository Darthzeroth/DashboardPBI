import os
import requests
import msal
from flask import Flask, render_template, jsonify
from dotenv import load_dotenv

# 1. Cargar variables de entorno desde el archivo .env
load_dotenv()

app = Flask(__name__)

# --- CONFIGURACIÓN ---
# Estas variables deben coincidir con las de tu archivo .env
CLIENT_ID = os.getenv('CLIENT_ID')
TENANT_ID = os.getenv('TENANT_ID')
PBI_USER = os.getenv('PBI_USER')
PBI_PASSWORD = os.getenv('PBI_PASSWORD')
GROUP_ID = os.getenv('GROUP_ID')   # ID del Workspace
REPORT_ID = os.getenv('REPORT_ID') # ID del Reporte

# Endpoint de autoridad de Azure (Entra ID)
AUTHORITY_URL = f'https://login.microsoftonline.com/{TENANT_ID}'

# Los permisos que necesitamos (Scope)
# Nota: Para Power BI, el scope suele ser este formato específico
SCOPE = ["https://analysis.windows.net/powerbi/api/Report.Read.All"]

# --- FUNCIONES AUXILIARES ---

def get_access_token():
    """
    Obtiene el token de acceso usando usuario y contraseña (ROPC Flow).
    ADVERTENCIA: Este método no funciona si la cuenta tiene MFA activo.
    """
    app_msal = msal.PublicClientApplication(
        CLIENT_ID, 
        authority=AUTHORITY_URL
    )

    # Intentamos obtener el token
    result = app_msal.acquire_token_by_username_password(
        PBI_USER, 
        PBI_PASSWORD, 
        scopes=SCOPE
    )

    if "access_token" in result:
        return result['access_token']
    else:
        # Imprimimos el error en la consola para depuración
        print(f"Error obteniendo token: {result.get('error')}")
        print(f"Descripción: {result.get('error_description')}")
        return None

def get_report_details(access_token):
    """
    Consulta la API de Power BI para obtener la EmbedURL del reporte.
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # URL para obtener detalles de un reporte en un grupo (workspace) específico
    api_url = f'https://api.powerbi.com/v1.0/myorg/groups/{GROUP_ID}/reports/{REPORT_ID}'
    
    response = requests.get(api_url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error API Power BI: {response.status_code} - {response.text}")
        return None

# --- RUTAS DE FLASK ---

@app.route('/')
def index():
    # 1. Obtener Token
    token = get_access_token()
    
    if not token:
        return "<h1>Error de Autenticación</h1><p>Revisa la consola de Python para ver el error (probablemente MFA o credenciales incorrectas).</p>", 401

    # 2. Obtener URL de Incrustación
    report_data = get_report_details(token)
    
    if not report_data:
        return "<h1>Error de Power BI</h1><p>No se pudo obtener la información del reporte. Revisa los IDs en el .env</p>", 404

    # 3. Renderizar la plantilla HTML
    # Pasamos los datos necesarios para el JS del frontend
    return render_template(
        'index.html',
        access_token=token,
        embed_url=report_data['embedUrl'],
        report_id=report_data['id']
    )

# --- INICIO DE LA APP ---

if __name__ == '__main__':
    # debug=True permite ver los errores en el navegador y recarga si cambias código
    print("Iniciando servidor Flask para Power BI Demo...")
    app.run(debug=True, port=5000)