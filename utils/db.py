import mysql.connector
from config import Config
import os
import re
import logging
from urllib.parse import urlparse, unquote

# Configurar logging
logger = logging.getLogger(__name__)
_warning_logged = False  # Variable para evitar logging repetitivo

def get_db_connection():
    # Detectar si estamos en Cloud Run
    is_cloud_run = os.getenv('K_SERVICE') is not None
    
    # Usar DATABASE_URL si está disponible (como la API de tickets)
    if hasattr(Config, 'DATABASE_URL') and Config.DATABASE_URL:
        url = Config.DATABASE_URL
        
        try:
            # Remover el prefijo mysql+pymysql://
            if url.startswith('mysql+pymysql://'):
                url_clean = url[17:]  # Remover 'mysql+pymysql://'
            elif url.startswith('mysql://'):
                url_clean = url[8:]  # Remover 'mysql://'
            else:
                url_clean = url
            
            # Parsear manualmente para manejar caracteres especiales en la contraseña
            # Formato esperado: user:password@host/database o user:password@/database?unix_socket=...
            
            # Buscar el último @ que separa credenciales del resto (puede haber @ en la contraseña)
            # Usar rfind para encontrar el último @
            at_pos = url_clean.rfind('@')
            
            if at_pos == -1:
                raise ValueError("No se encontró @ en DATABASE_URL")
            
            credentials_part = url_clean[:at_pos]
            rest_part = url_clean[at_pos + 1:]
            
            # Separar usuario y contraseña (el primer : separa usuario de contraseña)
            colon_pos = credentials_part.find(':')
            if colon_pos == -1:
                raise ValueError("No se encontró : en las credenciales")
            
            user = credentials_part[:colon_pos]
            password = credentials_part[colon_pos + 1:]
            
            # Parsear el resto (host/database o /database?params)
            unix_socket = None
            host = 'localhost'
            port = 3306
            database = None
            
            if rest_part.startswith('/'):
                # Formato: /database o /database?unix_socket=...
                if '?' in rest_part:
                    database_part, query_part = rest_part[1:].split('?', 1)
                    database = database_part
                    
                    # Parsear query params
                    params = {}
                    for param in query_part.split('&'):
                        if '=' in param:
                            key, value = param.split('=', 1)
                            params[key] = value
                    
                    if 'unix_socket' in params:
                        unix_socket = params['unix_socket']
                        if not unix_socket.startswith('/cloudsql/'):
                            unix_socket = f'/cloudsql/{unix_socket}'
                else:
                    database = rest_part[1:]
            else:
                # Formato: host:port/database o host/database
                if '/' in rest_part:
                    host_part, database = rest_part.split('/', 1)
                    if ':' in host_part:
                        host, port_str = host_part.split(':', 1)
                        try:
                            port = int(port_str)
                        except ValueError:
                            port = 3306
                    else:
                        host = host_part
                else:
                    host = rest_part
            
            if not database:
                raise ValueError("No se encontró el nombre de la base de datos")
            
            # Si estamos en Cloud Run y no hay unix_socket, intentar obtenerlo de variables de entorno
            if is_cloud_run and not unix_socket:
                # Intentar obtener de CLOUD_SQL_CONNECTION_NAME (formato: PROJECT:REGION:INSTANCE)
                cloud_sql_connection = os.getenv('CLOUD_SQL_CONNECTION_NAME')
                if cloud_sql_connection:
                    unix_socket = f'/cloudsql/{cloud_sql_connection}'
                    logger.info(f"🔗 Usando Cloud SQL connection: {unix_socket}")
            
            # Construir parámetros de conexión
            connection_params = {
                'user': user,
                'password': password,
                'database': database
            }
            
            # En Cloud Run con unix_socket, usar localhost sin puerto
            if unix_socket:
                connection_params['host'] = 'localhost'
                connection_params['unix_socket'] = unix_socket
            else:
                connection_params['host'] = host
                connection_params['port'] = port
            
            logger.info(f"🔗 Conectando a: host={connection_params.get('host')}, database={database}, unix_socket={unix_socket if unix_socket else 'None'}")
            
            return mysql.connector.connect(**connection_params)
            
        except Exception as e:
            # Si falla el parsing, usar configuración anterior (solo loguear una vez)
            global _warning_logged
            if not _warning_logged:
                logger.warning(f"⚠️ No se pudo parsear DATABASE_URL, usando configuración anterior: {str(e)}")
                _warning_logged = True
            
            # Si estamos en Cloud Run, intentar usar unix_socket
            connection_params = {
                'host': Config.DB_HOST,
                'user': Config.DB_USER,
                'password': Config.DB_PASSWORD,
                'database': Config.DB_NAME,
                'port': Config.DB_PORT
            }
            
            if is_cloud_run:
                cloud_sql_connection = os.getenv('CLOUD_SQL_CONNECTION_NAME')
                if cloud_sql_connection:
                    connection_params['host'] = 'localhost'
                    connection_params['unix_socket'] = f'/cloudsql/{cloud_sql_connection}'
                    connection_params.pop('port', None)  # No usar puerto con unix_socket
                    logger.info(f"🔗 Cloud Run: Usando unix_socket: {connection_params['unix_socket']}")
            
            return mysql.connector.connect(**connection_params)
    else:
        logger.info("🔄 Usando configuración anterior (sin DATABASE_URL)")
        # Fallback a la configuración anterior
        connection_params = {
            'host': Config.DB_HOST,
            'user': Config.DB_USER,
            'password': Config.DB_PASSWORD,
            'database': Config.DB_NAME,
            'port': Config.DB_PORT
        }
        
        # Si estamos en Cloud Run, intentar usar unix_socket
        if is_cloud_run:
            cloud_sql_connection = os.getenv('CLOUD_SQL_CONNECTION_NAME')
            if cloud_sql_connection:
                connection_params['host'] = 'localhost'
                connection_params['unix_socket'] = f'/cloudsql/{cloud_sql_connection}'
                connection_params.pop('port', None)  # No usar puerto con unix_socket
                logger.info(f"🔗 Cloud Run: Usando unix_socket: {connection_params['unix_socket']}")
        
        return mysql.connector.connect(**connection_params)
