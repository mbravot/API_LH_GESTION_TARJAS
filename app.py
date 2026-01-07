from flask import Flask, Blueprint
from flask_jwt_extended import JWTManager
from config import Config
from flask_cors import CORS
from datetime import timedelta
import os


# Crear la aplicación Flask
def create_app():
    app = Flask(__name__)
    
    # Configurar CORS
    CORS(app, resources={
        r"/*": {
            "origins": [
                "http://localhost:*", 
                "http://localhost:59494",
                "http://127.0.0.1:*", 
                "http://192.168.1.52:*", 
                "http://192.168.1.208:*", 
                "http://192.168.1.40:*",
                "http://192.168.1.60:*",
                "https://api-lh-gestion-tarjas-927498545444.us-central1.run.app",
                "https://gestion-la-hornilla.web.app",
                "https://gestion-la-hornilla.firebaseapp.com",
                "https://gestion-tarja.lahornilla.cl"
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "supports_credentials": True,
            "expose_headers": ["Content-Type", "Authorization"],
            "max_age": 3600
        }
    })

    # Configurar JWT
    app.config['JWT_SECRET_KEY'] = Config.JWT_SECRET_KEY
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=10)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=7)
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    app.config['JWT_HEADER_NAME'] = 'Authorization'
    app.config['JWT_HEADER_TYPE'] = 'Bearer'

    jwt = JWTManager(app)

    # Registrar los blueprints
    from blueprints.usuarios import usuarios_bp
    from blueprints.actividades import actividades_bp
    from blueprints.rendimientos import rendimientos_bp
    from blueprints.auth import auth_bp
    from blueprints.opciones import opciones_bp
    from blueprints.trabajadores import trabajadores_bp
    from blueprints.contratistas import contratistas_bp
    from blueprints.colaboradores import colaboradores_bp
    from blueprints.permisos import permisos_bp
    from blueprints.permisos_ausencia import permisos_ausencia_bp
    from blueprints.rendimientopropio import rendimientopropio_bp
    from blueprints.vacaciones import vacaciones_bp
    from blueprints.licencias import licencias_bp
    from blueprints.horas_trabajadas import horas_trabajadas_bp
    from blueprints.horas_extras import horas_extras_bp
    from blueprints.horas_extras_otroscecos import horas_extras_otroscecos_bp
    from blueprints.bono_especial import bono_especial_bp
    from blueprints.sueldos import sueldos_bp
    from blueprints.sucursales import sucursales_bp
    from blueprints.tarja_propio import tarja_propio_bp
    from blueprints.cambio_porcentaje import cambio_porcentaje_bp

    
    # Registrar blueprints
    app.register_blueprint(actividades_bp, url_prefix='/api/actividades')
    app.register_blueprint(rendimientos_bp, url_prefix='/api/rendimientos')
    app.register_blueprint(usuarios_bp, url_prefix='/api/usuarios')
    app.register_blueprint(contratistas_bp, url_prefix='/api/contratistas')
    app.register_blueprint(trabajadores_bp, url_prefix='/api/trabajadores')
    app.register_blueprint(opciones_bp, url_prefix="/api/opciones")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(colaboradores_bp, url_prefix='/api/colaboradores')
    app.register_blueprint(permisos_bp, url_prefix='/api/permisos')
    app.register_blueprint(permisos_ausencia_bp, url_prefix='/api/permisos-ausencia')
    app.register_blueprint(rendimientopropio_bp, url_prefix='/api/rendimientopropio')
    app.register_blueprint(vacaciones_bp, url_prefix='/api/vacaciones')
    app.register_blueprint(licencias_bp, url_prefix='/api/licencias')
    app.register_blueprint(horas_trabajadas_bp, url_prefix='/api/horas-trabajadas')
    app.register_blueprint(horas_extras_bp, url_prefix='/api/horas-extras')
    app.register_blueprint(horas_extras_otroscecos_bp, url_prefix='/api/horas-extras-otroscecos')
    app.register_blueprint(bono_especial_bp, url_prefix='/api/bono-especial')
    app.register_blueprint(sueldos_bp, url_prefix='/api/sueldos')
    app.register_blueprint(sucursales_bp, url_prefix='/api/sucursal')
    app.register_blueprint(tarja_propio_bp, url_prefix='/api/tarja-propio')
    app.register_blueprint(cambio_porcentaje_bp, url_prefix='/api/cambio-porcentaje')
    
    # Crear un nuevo blueprint para las rutas raíz
    root_bp = Blueprint('root_bp', __name__)
    
    # Health check para Cloud Run
    @root_bp.route('/health', methods=['GET'])
    def health_check():
        return {"status": "healthy", "service": "api-lh-gestion-tarjas"}, 200
    
    # Debug endpoint para verificar conectividad de BD
    @root_bp.route('/debug/db', methods=['GET'])
    def debug_db():
        try:
            from utils.db import get_db_connection
            import os
            
            # Información del entorno
            env_info = {
                "K_SERVICE": os.getenv('K_SERVICE'),
                "DATABASE_URL": os.getenv('DATABASE_URL'),
                "DB_HOST": os.getenv('DB_HOST'),
                "DB_USER": os.getenv('DB_USER'),
                "DB_NAME": os.getenv('DB_NAME')
            }
            
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return {
                "status": "success",
                "database": "connected",
                "test_query": result,
                "environment": env_info
            }, 200
        except Exception as e:
            return {
                "status": "error",
                "database": "disconnected",
                "error": str(e),
                "environment": env_info if 'env_info' in locals() else "No disponible"
            }, 500
    
    # Importar y registrar las rutas raíz
    from blueprints.auth import obtener_sucursales
    root_bp.add_url_rule('/sucursales/', 'obtener_sucursales', obtener_sucursales, methods=['GET', 'OPTIONS'])
    
    # Endpoint de prueba para licencias
    @root_bp.route('/test/licencias', methods=['GET'])
    def test_licencias():
        try:
            from utils.db import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Probar consulta a la tabla de licencias
            cursor.execute("SELECT COUNT(*) as total FROM tarja_fact_licenciamedica")
            result = cursor.fetchone()
            
            # Probar consulta a colaboradores
            cursor.execute("SELECT COUNT(*) as total FROM general_dim_colaborador")
            result2 = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return {
                "status": "success",
                "licencias_count": result['total'],
                "colaboradores_count": result2['total'],
                "message": "Conexión a BD y tablas funcionando correctamente"
            }, 200
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Error al conectar con la base de datos o tablas"
            }, 500
    
    # Registrar el blueprint raíz
    app.register_blueprint(root_bp, url_prefix="/api")

    return app

# Crear una única instancia de la aplicación
app = create_app()

if __name__ == '__main__':
    # Usar puerto 8080 para Cloud Run, 5000 para desarrollo local
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)

