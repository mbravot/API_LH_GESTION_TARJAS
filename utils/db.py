import mysql.connector
from config import Config
import os
import re
import logging

# Configurar logging
logger = logging.getLogger(__name__)

def get_db_connection():
    # Usar DATABASE_URL si está disponible (como la API de tickets)
    if hasattr(Config, 'DATABASE_URL') and Config.DATABASE_URL:
        logger.info(f"🔍 DATABASE_URL: {Config.DATABASE_URL}")
        
        # Parsear DATABASE_URL con formato de Cloud SQL
        # Formato: mysql+pymysql://user:password@/database?unix_socket=/cloudsql/instance
        url = Config.DATABASE_URL
        
        # Extraer componentes usando regex corregido
        pattern = r'mysql\+pymysql://([^:]+):([^@]+)@/([^?]+)\?unix_socket=([^/]+)/(.+)'
        match = re.match(pattern, url)
        
        if match:
            user, password, database, socket_prefix, instance = match.groups()
            logger.info(f"✅ Parseado correctamente:")
            logger.info(f"   User: {user}")
            logger.info(f"   Database: {database}")
            logger.info(f"   Instance: {instance}")
            
            # Para Cloud SQL con unix_socket, usar localhost
            connection_params = {
                'host': 'localhost',
                'user': user,
                'password': password,
                'database': database,
                'port': 3306,
                'unix_socket': f'/cloudsql/{instance}'
            }
            logger.info(f"🔗 Parámetros de conexión: {connection_params}")
            
            return mysql.connector.connect(**connection_params)
        else:
            logger.error(f"❌ No se pudo parsear DATABASE_URL con regex: {url}")
            logger.error(f"❌ Pattern no coincidió")
            
            # Intentar parsear manualmente
            try:
                # Remover mysql+pymysql://
                url_clean = url.replace('mysql+pymysql://', '').replace('mysql://', '')
                
                # Separar credenciales y resto
                if '@/' in url_clean:
                    credentials, rest = url_clean.split('@/', 1)
                    user, password = credentials.split(':', 1)
                    
                    # Separar database y parámetros
                    if '?' in rest:
                        database, params = rest.split('?', 1)
                        
                        # Extraer unix_socket
                        if 'unix_socket=' in params:
                            socket_part = params.split('unix_socket=', 1)[1]
                            # Remover /cloudsql/ si ya está presente
                            if socket_part.startswith('/cloudsql/'):
                                instance = socket_part.replace('/cloudsql/', '')
                            else:
                                instance = socket_part
                            
                            logger.info(f"✅ Parseado manualmente:")
                            logger.info(f"   User: {user}")
                            logger.info(f"   Database: {database}")
                            logger.info(f"   Instance: {instance}")
                            
                            connection_params = {
                                'host': 'localhost',
                                'user': user,
                                'password': password,
                                'database': database,
                                'port': 3306,
                                'unix_socket': f'/cloudsql/{instance}'
                            }
                            logger.info(f"🔗 Parámetros de conexión: {connection_params}")
                            
                            return mysql.connector.connect(**connection_params)
                
                logger.error(f"❌ Parseado manual también falló")
                
            except Exception as e:
                logger.error(f"❌ Error en parseado manual: {str(e)}")
            
            # Fallback para formato simple
            try:
                url_clean = url.replace('mysql+pymysql://', '').replace('mysql://', '')
                if '@' in url_clean:
                    credentials, rest = url_clean.split('@', 1)
                    user, password = credentials.split(':', 1)
                    if '/' in rest:
                        host, database = rest.split('/', 1)
                        # Verificar si hay puerto
                        if ':' in host:
                            host, port_str = host.split(':', 1)
                            try:
                                port = int(port_str)
                            except ValueError:
                                port = 3306
                        else:
                            port = 3306
                        
                        logger.info(f"🔄 Usando fallback con host: {host}, port: {port}")
                        return mysql.connector.connect(
                            host=host,
                            user=user,
                            password=password,
                            database=database,
                            port=port
                        )
                    else:
                        # Formato sin host (localhost implícito)
                        database = rest
                        logger.info(f"🔄 Usando fallback localhost")
                        return mysql.connector.connect(
                            host='localhost',
                            user=user,
                            password=password,
                            database=database,
                            port=3306
                        )
            except Exception as e:
                logger.error(f"❌ Error en fallback: {str(e)}")
    
    # Si no hay DATABASE_URL o falló todo, usar configuración anterior
    logger.info("🔄 Usando configuración anterior (sin DATABASE_URL o falló parsing)")
    
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
    
    logger.info(f"🔄 Usando configuración: host={db_host}, user={db_user}, database={db_name}, port={db_port}")
    
    return mysql.connector.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name,
        port=db_port
    )
