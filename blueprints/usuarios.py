from flask import Blueprint, jsonify, request
from utils.db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
import bcrypt
from datetime import date
import uuid


usuarios_bp = Blueprint('usuarios_bp', __name__)

def verificar_admin(usuario_id):
    """Verifica si el usuario tiene perfil de administrador (id_perfil = 3)"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_perfil FROM general_dim_usuario WHERE id = %s", (usuario_id,))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()
    return usuario and usuario['id_perfil'] == 3

def verificar_permiso_full(usuario_id):
    """Verifica si el usuario tiene permiso Full (id=6) para gestionar usuarios"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT up.id_permiso 
        FROM usuario_pivot_permiso_usuario up
        WHERE up.id_usuario = %s AND up.id_permiso = '6'
    """, (usuario_id,))
    permiso = cursor.fetchone()
    cursor.close()
    conn.close()
    return permiso is not None

# 🔹 Obtener todos los usuarios
@usuarios_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_usuarios():
    usuario_id = get_jwt_identity()
    if not verificar_permiso_full(usuario_id):
        return jsonify({"error": "No autorizado. Se requiere permiso Full para gestionar usuarios"}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
    SELECT 
        u.id, u.usuario, u.correo, u.id_sucursalactiva, u.id_estado, u.id_rol, u.id_perfil, u.fecha_creacion, 
        s.nombre AS nombre_sucursal,
        CASE 
            WHEN u.nombre IS NOT NULL AND u.nombre != '' 
            THEN TRIM(CONCAT_WS(' ', u.nombre, u.apellido_paterno, u.apellido_materno))
            ELSE u.usuario
        END AS nombre_completo
    FROM general_dim_usuario u
    LEFT JOIN general_dim_sucursal s ON u.id_sucursalactiva = s.id
    ORDER BY nombre_completo ASC
""")

        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(usuarios), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Crear nuevo usuario (solo admin)
@usuarios_bp.route('/', methods=['POST'])
@jwt_required()
def crear_usuario():
    usuario_id = get_jwt_identity()
    if not verificar_permiso_full(usuario_id):
        return jsonify({"error": "No autorizado. Se requiere permiso Full para gestionar usuarios"}), 403

    data = request.json
    
    usuario = data.get('usuario')
    correo = data.get('correo')
    clave = data.get('clave')
    id_sucursalactiva = data.get('id_sucursalactiva')
    nombre = data.get('nombre')
    apellido_paterno = data.get('apellido_paterno')
    apellido_materno = data.get('apellido_materno')
    permisos = data.get('permisos', [])  # Lista opcional de permisos
    sucursales_adicionales = data.get('sucursales_adicionales', [])  # Lista opcional de sucursales adicionales


    # Convertir id_sucursalactiva a entero si es necesario
    if id_sucursalactiva:
        try:
            id_sucursalactiva = int(id_sucursalactiva)
        except (ValueError, TypeError):
            return jsonify({"error": "id_sucursalactiva debe ser un número válido"}), 400

    # Validar campos obligatorios
    if not usuario or not correo or not clave or not id_sucursalactiva or not nombre or not apellido_paterno:
        return jsonify({"error": "Faltan campos obligatorios: usuario, correo, clave, id_sucursalactiva, nombre, apellido_paterno"}), 400

    # Validar que la sucursal existe
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que la sucursal existe
        cursor.execute("SELECT id FROM general_dim_sucursal WHERE id = %s", (id_sucursalactiva,))
        sucursal = cursor.fetchone()
        if not sucursal:
            cursor.close()
            conn.close()
            return jsonify({"error": "La sucursal especificada no existe"}), 400



        # Verificar que el usuario no existe
        cursor.execute("SELECT id FROM general_dim_usuario WHERE usuario = %s OR correo = %s", (usuario, correo))
        usuario_existente = cursor.fetchone()
        if usuario_existente:
            cursor.close()
            conn.close()
            return jsonify({"error": "Ya existe un usuario con ese nombre de usuario o correo"}), 400

        # Generar hash bcrypt
        salt = bcrypt.gensalt()
        clave_encriptada = bcrypt.hashpw(clave.encode('utf-8'), salt).decode('utf-8')

        # Valores por defecto para campos ocultos
        id_estado = 1  # Activo por defecto
        id_rol = 3     # Usuario común por defecto
        id_perfil = 1  # Perfil 1 por defecto

        # Generar UUID para el usuario
        usuario_id = str(uuid.uuid4())

        # Manejar valores null correctamente
        apellido_materno_clean = apellido_materno if apellido_materno is not None and apellido_materno.strip() != '' else None
        
        # Insertar usuario
        cursor.execute("""
            INSERT INTO general_dim_usuario (
                id, usuario, correo, clave, id_sucursalactiva, 
                id_estado, id_rol, id_perfil, fecha_creacion,
                nombre, apellido_paterno, apellido_materno
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (usuario_id, usuario, correo, clave_encriptada, id_sucursalactiva, 
              id_estado, id_rol, id_perfil, date.today(), nombre, apellido_paterno, apellido_materno_clean))
        
        # Asignar permiso a la app (id_app = 3)
        pivot_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO usuario_pivot_app_usuario (id, id_usuario, id_app)
            VALUES (%s, %s, %s)
        """, (pivot_id, usuario_id, 3))
        
        # Asignar permisos opcionales si se proporcionan
        if permisos and isinstance(permisos, list):
            for permiso_id in permisos:
                cursor.execute("""
                    INSERT INTO usuario_pivot_permiso_usuario (id_usuario, id_permiso)
                    VALUES (%s, %s)
                """, (usuario_id, permiso_id))
        
        # Asignar sucursales adicionales si se proporcionan
        if sucursales_adicionales and isinstance(sucursales_adicionales, list):
            for sucursal_id in sucursales_adicionales:
                cursor.execute("""
                    INSERT INTO usuario_pivot_sucursal_usuario (id_sucursal, id_usuario)
                    VALUES (%s, %s)
                """, (sucursal_id, usuario_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Usuario creado correctamente",
            "id": usuario_id,
            "usuario": usuario,
            "correo": correo,
            "id_sucursalactiva": id_sucursalactiva,
            "nombre": nombre,
            "apellido_paterno": apellido_paterno,
            "apellido_materno": apellido_materno,
            "permisos_asignados": permisos,
            "sucursales_adicionales": sucursales_adicionales
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar usuarios
@usuarios_bp.route('/<string:usuario_id>', methods=['PUT'])
@jwt_required()
def editar_usuario(usuario_id):
    usuario_logueado = get_jwt_identity()
    if not verificar_permiso_full(usuario_logueado):
        return jsonify({"error": "No autorizado. Se requiere permiso Full para gestionar usuarios"}), 403

    data = request.json
    
    # Validar que el usuario_id sea válido
    if not usuario_id or usuario_id.strip() == '':
        return jsonify({"error": "ID de usuario inválido"}), 400
    
    usuario_nombre = data.get('usuario')
    correo = data.get('correo')
    clave = data.get('clave')  # Opcional, solo si se quiere cambiar
    id_sucursalactiva = data.get('id_sucursalactiva')
    nombre = data.get('nombre')
    apellido_paterno = data.get('apellido_paterno')
    apellido_materno = data.get('apellido_materno')
    permisos = data.get('permisos', [])  # Lista opcional de permisos
    sucursales_adicionales = data.get('sucursales_adicionales', [])  # Lista opcional de sucursales adicionales

    id_estado = data.get('id_estado')  # Opcional, para cambiar estado

    # Convertir id_sucursalactiva a entero si es necesario
    if id_sucursalactiva:
        try:
            id_sucursalactiva = int(id_sucursalactiva)
        except (ValueError, TypeError):
            return jsonify({"error": "id_sucursalactiva debe ser un número válido"}), 400

    # Convertir id_estado a entero si es necesario
    if id_estado:
        try:
            id_estado = int(id_estado)
        except (ValueError, TypeError):
            return jsonify({"error": "id_estado debe ser un número válido"}), 400

    # Validar campos obligatorios
    if not usuario_nombre or not correo or not id_sucursalactiva or not nombre or not apellido_paterno:
        return jsonify({"error": "Faltan campos obligatorios: usuario, correo, id_sucursalactiva, nombre, apellido_paterno"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que el usuario a editar existe
        cursor.execute("SELECT id, usuario FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario_existente = cursor.fetchone()
        if not usuario_existente:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        # Debug: Log del usuario encontrado
        print(f"DEBUG: Usuario encontrado - ID: {usuario_existente['id']}, Usuario: {usuario_existente['usuario']}")

        # Verificar que la sucursal existe
        cursor.execute("SELECT id FROM general_dim_sucursal WHERE id = %s", (id_sucursalactiva,))
        sucursal = cursor.fetchone()
        if not sucursal:
            cursor.close()
            conn.close()
            return jsonify({"error": "La sucursal especificada no existe"}), 400



        # Verificar que no existe otro usuario con el mismo nombre o correo
        cursor.execute("SELECT id FROM general_dim_usuario WHERE (usuario = %s OR correo = %s) AND id != %s", 
                      (usuario_nombre, correo, usuario_id))
        usuario_duplicado = cursor.fetchone()
        if usuario_duplicado:
            cursor.close()
            conn.close()
            return jsonify({"error": "Ya existe otro usuario con ese nombre de usuario o correo"}), 400

        # Manejar valores null correctamente
        apellido_materno_clean = apellido_materno if apellido_materno is not None and apellido_materno.strip() != '' else None
        
        # Preparar la actualización
        if clave:  # Solo si se envió una nueva clave
            salt = bcrypt.gensalt()
            clave_encriptada = bcrypt.hashpw(clave.encode('utf-8'), salt).decode('utf-8')
            sql = """
                UPDATE general_dim_usuario 
                SET usuario = %s, correo = %s, clave = %s, id_sucursalactiva = %s, id_estado = %s,
                    nombre = %s, apellido_paterno = %s, apellido_materno = %s
                WHERE id = %s
            """
            valores = (usuario_nombre, correo, clave_encriptada, id_sucursalactiva, id_estado, 
                      nombre, apellido_paterno, apellido_materno_clean, usuario_id)
        else:
            sql = """
                UPDATE general_dim_usuario 
                SET usuario = %s, correo = %s, id_sucursalactiva = %s, id_estado = %s,
                    nombre = %s, apellido_paterno = %s, apellido_materno = %s
                WHERE id = %s
            """
            valores = (usuario_nombre, correo, id_sucursalactiva, id_estado, 
                      nombre, apellido_paterno, apellido_materno_clean, usuario_id)
        
        # Debug: Log de la consulta y valores
        print(f"DEBUG: SQL: {sql}")
        print(f"DEBUG: Valores: {valores}")
        print(f"DEBUG: Usuario ID: {usuario_id} (tipo: {type(usuario_id)})")
        print(f"DEBUG: Longitud del ID: {len(str(usuario_id))}")
        print(f"DEBUG: ID como string: '{str(usuario_id)}'")
        
        # Verificar que el ID no esté vacío o sea inválido
        if not usuario_id or str(usuario_id).strip() == '':
            cursor.close()
            conn.close()
            return jsonify({"error": "ID de usuario inválido o vacío"}), 400
        
        try:
            cursor.execute(sql, valores)
            filas_afectadas = cursor.rowcount
            print(f"DEBUG: Consulta ejecutada exitosamente. Filas afectadas: {filas_afectadas}")
        except Exception as sql_error:
            print(f"DEBUG: Error SQL específico: {sql_error}")
            print(f"DEBUG: Tipo de error: {type(sql_error)}")
            cursor.close()
            conn.close()
            return jsonify({"error": f"Error en la consulta SQL: {str(sql_error)}"}), 500
        
        # Manejar permisos si se proporcionan
        if permisos is not None and isinstance(permisos, list):
            # Eliminar permisos existentes del usuario
            cursor.execute("""
                DELETE FROM usuario_pivot_permiso_usuario 
                WHERE id_usuario = %s
            """, (usuario_id,))
            
            # Asignar nuevos permisos
            for permiso_id in permisos:
                cursor.execute("""
                    INSERT INTO usuario_pivot_permiso_usuario (id_usuario, id_permiso)
                    VALUES (%s, %s)
                """, (usuario_id, permiso_id))
        
        # Manejar sucursales adicionales si se proporcionan
        if sucursales_adicionales is not None and isinstance(sucursales_adicionales, list):
            # Eliminar sucursales adicionales existentes del usuario
            cursor.execute("""
                DELETE FROM usuario_pivot_sucursal_usuario 
                WHERE id_usuario = %s
            """, (usuario_id,))
            
            # Asignar nuevas sucursales adicionales
            for sucursal_id in sucursales_adicionales:
                cursor.execute("""
                    INSERT INTO usuario_pivot_sucursal_usuario (id_sucursal, id_usuario)
                    VALUES (%s, %s)
                """, (sucursal_id, usuario_id))
        
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "message": "Usuario actualizado correctamente",
            "usuario": usuario_nombre,
            "correo": correo,
            "id_sucursalactiva": id_sucursalactiva,
            "id_estado": id_estado,
            "nombre": nombre,
            "apellido_paterno": apellido_paterno,
            "apellido_materno": apellido_materno,
            "permisos_actualizados": permisos if permisos is not None else "No modificados",
            "sucursales_adicionales": sucursales_adicionales if sucursales_adicionales is not None else "No modificadas",
            "filas_afectadas": filas_afectadas
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Obtener sucursales de un usuario específico
@usuarios_bp.route('/<string:usuario_id>/sucursales', methods=['GET'])
@jwt_required()
def obtener_sucursales_usuario(usuario_id):
    """Obtener sucursales adicionales de un usuario específico"""
    usuario_logueado = get_jwt_identity()
    if not verificar_permiso_full(usuario_logueado):
        return jsonify({"error": "No autorizado. Se requiere permiso Full para gestionar usuarios"}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que el usuario existe
        cursor.execute("SELECT id FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario_existente = cursor.fetchone()
        if not usuario_existente:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        # Obtener sucursales del usuario
        cursor.execute("""
            SELECT 
                ps.id_sucursal,
                s.nombre as nombre_sucursal,
                s.ubicacion,
                s.id_empresa,
                s.id_sucursaltipo
            FROM usuario_pivot_sucursal_usuario ps
            LEFT JOIN general_dim_sucursal s ON ps.id_sucursal = s.id
            WHERE ps.id_usuario = %s
            ORDER BY s.nombre ASC
        """, (usuario_id,))
        
        sucursales = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            "usuario_id": usuario_id,
            "sucursales": sucursales,
            "total": len(sucursales)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Obtener permisos de un usuario específico
@usuarios_bp.route('/<string:usuario_id>/permisos', methods=['GET'])
@jwt_required()
def obtener_permisos_usuario(usuario_id):
    """Obtener permisos actuales de un usuario específico"""
    usuario_logueado = get_jwt_identity()
    if not verificar_permiso_full(usuario_logueado):
        return jsonify({"error": "No autorizado. Se requiere permiso Full para gestionar usuarios"}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que el usuario existe
        cursor.execute("SELECT id FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario_existente = cursor.fetchone()
        if not usuario_existente:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        # Obtener permisos del usuario
        cursor.execute("""
            SELECT 
                up.id_permiso,
                p.nombre as nombre_permiso,
                p.id_app,
                p.id_estado
            FROM usuario_pivot_permiso_usuario up
            LEFT JOIN usuario_dim_permiso p ON up.id_permiso = p.id
            WHERE up.id_usuario = %s
            ORDER BY p.nombre ASC
        """, (usuario_id,))
        
        permisos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            "usuario_id": usuario_id,
            "permisos": permisos,
            "total": len(permisos)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#Eliminar usuario
@usuarios_bp.route('/<string:usuario_id>', methods=['DELETE'])
@jwt_required()
def eliminar_usuario(usuario_id):
    usuario_logueado = get_jwt_identity()
    if not verificar_permiso_full(usuario_logueado):
        return jsonify({"error": "No autorizado. Se requiere permiso Full para gestionar usuarios"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Verificar si el usuario logueado es administrador
    cursor.execute("SELECT id_perfil FROM general_dim_usuario WHERE id = %s", (usuario_logueado,))
    usuario = cursor.fetchone()
    if not usuario or usuario['id_perfil'] != 3:
        cursor.close()
        conn.close()
        return jsonify({"error": "No autorizado"}), 403

    try:
        cursor.execute("DELETE FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Usuario eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Obtener permisos disponibles para la app (id_app = 3)
@usuarios_bp.route('/permisos-disponibles', methods=['GET'])
@jwt_required()
def obtener_permisos_disponibles():
    """Obtener permisos disponibles para la app (id_app = 3)"""
    usuario_id = get_jwt_identity()
    if not verificar_permiso_full(usuario_id):
        return jsonify({"error": "No autorizado. Se requiere permiso Full para gestionar usuarios"}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, nombre, id_app, id_estado
            FROM usuario_dim_permiso 
            WHERE id_app = 3 AND id_estado = 1
            ORDER BY nombre ASC
        """)
        
        permisos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            "permisos": permisos,
            "total": len(permisos)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Obtener sucursales disponibles
@usuarios_bp.route('/sucursales-disponibles', methods=['GET'])
@jwt_required()
def obtener_sucursales_disponibles():
    """Obtener sucursales disponibles para asignar a usuarios"""
    usuario_id = get_jwt_identity()
    if not verificar_permiso_full(usuario_id):
        return jsonify({"error": "No autorizado. Se requiere permiso Full para gestionar usuarios"}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, nombre, ubicacion, id_empresa, id_sucursaltipo
            FROM general_dim_sucursal 
            WHERE id_estado = 1
            ORDER BY nombre ASC
        """)
        
        sucursales = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            "sucursales": sucursales,
            "total": len(sucursales)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@usuarios_bp.route('/sucursal', methods=['GET'])
@jwt_required()
def obtener_sucursal_usuario():
    try:
        usuario_id = get_jwt_identity()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        cursor.close()
        conn.close()

        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "Usuario no encontrado o sin sucursal asignada"}), 404

        return jsonify({"id_sucursal": usuario['id_sucursalactiva']}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@usuarios_bp.route('/sucursal-activa', methods=['POST'])
@jwt_required()
def actualizar_sucursal_activa():
    try:
        usuario_id = get_jwt_identity()
        data = request.json
        nueva_sucursal = data.get("id_sucursal")

        if not nueva_sucursal:
            return jsonify({"error": "Sucursal no especificada"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

            # Verificar que el usuario tenga acceso a la sucursal
        cursor.execute("""
                SELECT 1 
                FROM usuario_pivot_sucursal_usuario 
                WHERE id_usuario = %s AND id_sucursal = %s
            """, (usuario_id, nueva_sucursal))
            
        if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({"error": "No tienes acceso a esta sucursal"}), 403

            # Actualizar la sucursal activa
        cursor.execute("""
                UPDATE general_dim_usuario 
                SET id_sucursalactiva = %s 
                WHERE id = %s
            """, (nueva_sucursal, usuario_id))
            
        conn.commit()

            # Obtener el nombre de la sucursal para la respuesta
        cursor.execute("""
                SELECT nombre 
                FROM general_dim_sucursal 
                WHERE id = %s
            """, (nueva_sucursal,))
            
        sucursal = cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify({
                "message": "Sucursal actualizada correctamente",
                "id_sucursal": nueva_sucursal,
                "sucursal_nombre": sucursal['nombre'] if sucursal else None
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Obtener sucursal activa del usuario logueado
@usuarios_bp.route('/sucursal-activa', methods=['GET'])
@jwt_required()
def obtener_sucursal_activa():
    usuario_id = get_jwt_identity()

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        cursor.close()
        conn.close()

        if not usuario or usuario['id_sucursalactiva'] is None:
            return jsonify({"error": "No se encontró la sucursal activa"}), 404

        return jsonify({"sucursal_activa": usuario['id_sucursalactiva']}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener colaboradores según la sucursal activa del usuario logueado o por parámetro
@usuarios_bp.route('/colaboradores', methods=['GET'])
@jwt_required()
def obtener_colaboradores():
    usuario_id = get_jwt_identity()
    id_sucursal = request.args.get('id_sucursal')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if not id_sucursal:
        # Buscar sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        id_sucursal = usuario['id_sucursalactiva']
    # Buscar colaboradores activos de la sucursal
    cursor.execute("""
        SELECT id, nombre, apellido_paterno, apellido_materno, rut, codigo_verificador, id_cargo
        FROM general_dim_colaborador
        WHERE id_sucursal = %s AND id_estado = 1
        ORDER BY nombre, apellido_paterno
    """, (id_sucursal,))
    colaboradores = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(colaboradores), 200

# Obtener todas las sucursales disponibles (para crear usuarios)
@usuarios_bp.route('/sucursales', methods=['GET'])
@jwt_required()
def obtener_sucursales():
    usuario_id = get_jwt_identity()
    if not verificar_admin(usuario_id):
        return jsonify({"error": "No autorizado"}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener solo sucursales con id_sucursaltipo = 1
        cursor.execute("""
            SELECT id, nombre, ubicacion
            FROM general_dim_sucursal
            WHERE id_sucursaltipo = 1
            ORDER BY nombre ASC
        """)
        
        sucursales = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(sucursales), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener sucursales permitidas de un usuario
@usuarios_bp.route('/<string:usuario_id>/sucursales-permitidas', methods=['GET'])
@jwt_required()
def obtener_sucursales_permitidas(usuario_id):
    usuario_logueado = get_jwt_identity()
    if not verificar_admin(usuario_logueado):
        return jsonify({"error": "No autorizado"}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener las sucursales permitidas del usuario
        cursor.execute("""
            SELECT s.id, s.nombre, s.ubicacion
            FROM general_dim_sucursal s
            INNER JOIN usuario_pivot_sucursal_usuario p ON s.id = p.id_sucursal
            WHERE p.id_usuario = %s AND s.id_sucursaltipo = 1
            ORDER BY s.nombre ASC
        """, (usuario_id,))
        
        sucursales_permitidas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(sucursales_permitidas), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Asignar sucursales permitidas a un usuario
@usuarios_bp.route('/<string:usuario_id>/sucursales-permitidas', methods=['POST'])
@jwt_required()
def asignar_sucursales_permitidas(usuario_id):
    usuario_logueado = get_jwt_identity()
    if not verificar_admin(usuario_logueado):
        return jsonify({"error": "No autorizado"}), 403

    data = request.json
    sucursales_ids = data.get('sucursales_ids', [])  # Lista de IDs de sucursales

    if not isinstance(sucursales_ids, list):
        return jsonify({"error": "sucursales_ids debe ser una lista"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que el usuario existe
        cursor.execute("SELECT id FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no encontrado"}), 404

        # Verificar que todas las sucursales existen y son del tipo correcto
        if sucursales_ids:
            placeholders = ','.join(['%s'] * len(sucursales_ids))
            cursor.execute(f"""
                SELECT id FROM general_dim_sucursal 
                WHERE id IN ({placeholders}) AND id_sucursaltipo = 1
            """, sucursales_ids)
            sucursales_validas = cursor.fetchall()
            
            if len(sucursales_validas) != len(sucursales_ids):
                cursor.close()
                conn.close()
                return jsonify({"error": "Una o más sucursales no existen o no son del tipo correcto"}), 400

        # Eliminar todas las asignaciones actuales del usuario
        cursor.execute("DELETE FROM usuario_pivot_sucursal_usuario WHERE id_usuario = %s", (usuario_id,))
        
        # Insertar las nuevas asignaciones
        if sucursales_ids:
            for sucursal_id in sucursales_ids:
                cursor.execute("""
                    INSERT INTO usuario_pivot_sucursal_usuario (id_sucursal, id_usuario)
                    VALUES (%s, %s)
                """, (sucursal_id, usuario_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Sucursales permitidas asignadas correctamente",
            "usuario_id": usuario_id,
            "sucursales_asignadas": len(sucursales_ids)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Eliminar todas las sucursales permitidas de un usuario
@usuarios_bp.route('/<string:usuario_id>/sucursales-permitidas', methods=['DELETE'])
@jwt_required()
def eliminar_sucursales_permitidas(usuario_id):
    usuario_logueado = get_jwt_identity()
    if not verificar_admin(usuario_logueado):
        return jsonify({"error": "No autorizado"}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el usuario existe
        cursor.execute("SELECT id FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no encontrado"}), 404

        # Eliminar todas las asignaciones del usuario
        cursor.execute("DELETE FROM usuario_pivot_sucursal_usuario WHERE id_usuario = %s", (usuario_id,))
        filas_eliminadas = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Sucursales permitidas eliminadas correctamente",
            "usuario_id": usuario_id,
            "sucursales_eliminadas": filas_eliminadas
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener todas las aplicaciones disponibles
@usuarios_bp.route('/apps', methods=['GET'])
@jwt_required()
def obtener_apps():
    usuario_id = get_jwt_identity()
    if not verificar_admin(usuario_id):
        return jsonify({"error": "No autorizado"}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, nombre
            FROM general_dim_app
            ORDER BY nombre ASC
        """)
        
        apps = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(apps), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener aplicaciones permitidas de un usuario
@usuarios_bp.route('/<string:usuario_id>/apps-permitidas', methods=['GET'])
@jwt_required()
def obtener_apps_permitidas(usuario_id):
    usuario_logueado = get_jwt_identity()
    if not verificar_admin(usuario_logueado):
        return jsonify({"error": "No autorizado"}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener las aplicaciones permitidas del usuario
        cursor.execute("""
            SELECT a.id, a.nombre
            FROM general_dim_app a
            INNER JOIN usuario_pivot_app_usuario p ON a.id = p.id_app
            WHERE p.id_usuario = %s
            ORDER BY a.nombre ASC
        """, (usuario_id,))
        
        apps_permitidas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(apps_permitidas), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Asignar aplicaciones permitidas a un usuario
@usuarios_bp.route('/<string:usuario_id>/apps-permitidas', methods=['POST'])
@jwt_required()
def asignar_apps_permitidas(usuario_id):
    usuario_logueado = get_jwt_identity()
    if not verificar_admin(usuario_logueado):
        return jsonify({"error": "No autorizado"}), 403

    data = request.json
    apps_ids = data.get('apps_ids', [])  # Lista de IDs de aplicaciones

    if not isinstance(apps_ids, list):
        return jsonify({"error": "apps_ids debe ser una lista"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que el usuario existe
        cursor.execute("SELECT id FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no encontrado"}), 404

        # Verificar que todas las aplicaciones existen
        if apps_ids:
            placeholders = ','.join(['%s'] * len(apps_ids))
            cursor.execute(f"""
                SELECT id FROM general_dim_app 
                WHERE id IN ({placeholders})
            """, apps_ids)
            apps_validas = cursor.fetchall()
            
            if len(apps_validas) != len(apps_ids):
                cursor.close()
                conn.close()
                return jsonify({"error": "Una o más aplicaciones no existen"}), 400

        # Eliminar todas las asignaciones actuales del usuario
        cursor.execute("DELETE FROM usuario_pivot_app_usuario WHERE id_usuario = %s", (usuario_id,))
        
        # Insertar las nuevas asignaciones
        if apps_ids:
            for app_id in apps_ids:
                # Generar UUID para el id de la tabla pivote
                pivot_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO usuario_pivot_app_usuario (id, id_usuario, id_app)
                    VALUES (%s, %s, %s)
                """, (pivot_id, usuario_id, app_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Aplicaciones permitidas asignadas correctamente",
            "usuario_id": usuario_id,
            "apps_asignadas": len(apps_ids)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Eliminar todas las aplicaciones permitidas de un usuario
@usuarios_bp.route('/<string:usuario_id>/apps-permitidas', methods=['DELETE'])
@jwt_required()
def eliminar_apps_permitidas(usuario_id):
    usuario_logueado = get_jwt_identity()
    if not verificar_admin(usuario_logueado):
        return jsonify({"error": "No autorizado"}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el usuario existe
        cursor.execute("SELECT id FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no encontrado"}), 404

        # Eliminar todas las asignaciones del usuario
        cursor.execute("DELETE FROM usuario_pivot_app_usuario WHERE id_usuario = %s", (usuario_id,))
        filas_eliminadas = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Aplicaciones permitidas eliminadas correctamente",
            "usuario_id": usuario_id,
            "apps_eliminadas": filas_eliminadas
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
