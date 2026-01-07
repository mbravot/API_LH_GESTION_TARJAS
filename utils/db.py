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
            
            # Decodificar usuario y contraseña (pueden estar URL-encoded)
            user = unquote(user)
            password = unquote(password)
            
            # Validar que el usuario extraído sea razonable (no esté vacío o muy corto)
            if not user or len(user) < 3:
                raise ValueError(f"Usuario extraído del DATABASE_URL parece inválido: '{user}'")
            
            # Si hay variables de entorno disponibles, preferirlas sobre el DATABASE_URL parseado
            # Esto es especialmente útil en Cloud Run donde las variables pueden estar mejor configuradas
            if os.getenv('DB_USER'):
                logger.info(f"🔄 Variable DB_USER encontrada, usando en lugar de usuario del DATABASE_URL")
                raise ValueError("Usar variables de entorno en lugar de DATABASE_URL")
            
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
            
            # Construir parámetros de conexión
            connection_params = {
                'user': user,
                'password': password,
                'database': database
            }
            
            # Solo usar unix_socket si está explícitamente en el DATABASE_URL
            # No intentar adivinarlo automáticamente
            if unix_socket:
                connection_params['host'] = 'localhost'
                connection_params['unix_socket'] = unix_socket
            else:
                connection_params['host'] = host
                connection_params['port'] = port
            
            logger.info(f"🔗 Conectando a: host={connection_params.get('host')}, user={user}, database={database}, unix_socket={unix_socket if unix_socket else 'None'}")
            
            try:
                return mysql.connector.connect(**connection_params)
            except mysql.connector.Error as db_error:
                # Si la conexión falla, loguear el error y lanzar excepción más clara
                logger.error(f"❌ Error de conexión a BD: {str(db_error)}")
                logger.error(f"❌ Parámetros usados: host={connection_params.get('host')}, user={user}, database={database}")
                raise
            
        except Exception as e:
            # Si falla el parsing, usar configuración anterior (solo loguear una vez)
            global _warning_logged
            if not _warning_logged:
                logger.warning(f"⚠️ No se pudo parsear DATABASE_URL, usando configuración anterior: {str(e)}")
                logger.warning(f"⚠️ DATABASE_URL recibida: {url[:50]}..." if len(url) > 50 else f"⚠️ DATABASE_URL recibida: {url}")
                _warning_logged = True
            
            # Intentar usar variables de entorno directamente si están disponibles
            # Esto es útil cuando DATABASE_URL no se puede parsear pero las variables están disponibles
            # Priorizar variables de entorno sobre Config para Cloud Run
            db_user = os.getenv('DB_USER')
            if not db_user:
                db_user = Config.DB_USER
            
            db_password = os.getenv('DB_PASSWORD')
            if not db_password:
                db_password = Config.DB_PASSWORD
                
            db_host = os.getenv('DB_HOST')
            if not db_host:
                db_host = Config.DB_HOST
                
            db_name = os.getenv('DB_NAME')
            if not db_name:
                db_name = Config.DB_NAME
                
            db_port_str = os.getenv('DB_PORT')
            if db_port_str:
                try:
                    db_port = int(db_port_str)
                except ValueError:
                    db_port = Config.DB_PORT
            else:
                db_port = Config.DB_PORT
            
            # Validar que tenemos valores válidos
            if not db_user or not db_password or not db_name:
                raise ValueError(f"Faltan credenciales de BD: user={db_user}, password={'***' if db_password else None}, database={db_name}")
            
            logger.info(f"🔄 Usando fallback: host={db_host}, user={db_user}, database={db_name}, port={db_port}")
            
            try:
                return mysql.connector.connect(
                    host=db_host,
                    user=db_user,
                    password=db_password,
                    database=db_name,
                    port=db_port
                )
            except mysql.connector.Error as db_error:
                logger.error(f"❌ Error de conexión en fallback: {str(db_error)}")
                logger.error(f"❌ Parámetros usados: host={db_host}, user={db_user}, database={db_name}, port={db_port}")
                raise
    else:
        logger.info("🔄 Usando configuración anterior (sin DATABASE_URL)")
        # Intentar usar variables de entorno directamente si están disponibles
        # Priorizar variables de entorno sobre Config para Cloud Run
        db_user = os.getenv('DB_USER')
        if not db_user:
            db_user = Config.DB_USER
            
        db_password = os.getenv('DB_PASSWORD')
        if not db_password:
            db_password = Config.DB_PASSWORD
            
        db_host = os.getenv('DB_HOST')
        if not db_host:
            db_host = Config.DB_HOST
            
        db_name = os.getenv('DB_NAME')
        if not db_name:
            db_name = Config.DB_NAME
            
        db_port_str = os.getenv('DB_PORT')
        if db_port_str:
            try:
                db_port = int(db_port_str)
            except ValueError:
                db_port = Config.DB_PORT
        else:
            db_port = Config.DB_PORT
        
        # Validar que tenemos valores válidos
        if not db_user or not db_password or not db_name:
            raise ValueError(f"Faltan credenciales de BD: user={db_user}, password={'***' if db_password else None}, database={db_name}")
        
        logger.info(f"🔄 Usando configuración: host={db_host}, user={db_user}, database={db_name}, port={db_port}")
        
        try:
            return mysql.connector.connect(
                host=db_host,
                user=db_user,
                password=db_password,
                database=db_name,
                port=db_port
            )
        except mysql.connector.Error as db_error:
            logger.error(f"❌ Error de conexión: {str(db_error)}")
            logger.error(f"❌ Parámetros usados: host={db_host}, user={db_user}, database={db_name}, port={db_port}")
            raise
