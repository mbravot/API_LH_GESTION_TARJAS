import os
from dotenv import load_dotenv

load_dotenv()  # Carga las variables del archivo .env

class Config:
    DEBUG = os.getenv("DEBUG", "True") == "True"
    
    # Usar DATABASE_URL como la API de tickets
    DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://UserApp:&8y7c()tu9t/+,6`@localhost/lahornilla_base_normalizada")
    
    # Configuración automática para Cloud SQL
    if os.getenv('K_SERVICE'):  # Está en Cloud Run
        DB_HOST = 'localhost'
        DB_PORT = 3306
    else:
        # Para desarrollo local, usar Cloud SQL Proxy
        DB_HOST = 'localhost'
        DB_PORT = 3306
    
    DB_USER = os.getenv("DB_USER", "UserApp")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "&8y7c()tu9t/+,6`")
    DB_NAME = os.getenv("DB_NAME", "lahornilla_base_normalizada")
    
    JWT_SECRET_KEY = 'Inicio01*'  # ✅ Esta clave es usada por Flask-JWT-Extended
    SECRET_KEY = 'Inicio01*'
    DEBUG = True
