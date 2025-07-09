from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
from datetime import datetime, date
import uuid

permisos_bp = Blueprint('permisos_bp', __name__)

def format_fecha(fecha):
    if isinstance(fecha, (date, datetime)):
        return fecha.strftime('%Y-%m-%d')
    return fecha

# 📌 Obtener permisos del usuario autenticado
@permisos_bp.route('/usuario/actual', methods=['GET'])
@jwt_required()
def obtener_permisos_usuario_actual():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener permisos del usuario autenticado
        cursor.execute("""
            SELECT 
                p.id,
                p.nombre,
                p.id_app,
                p.id_estado
            FROM usuario_dim_permiso p
            JOIN usuario_pivot_permiso_usuario ppu ON p.id = ppu.id_permiso
            WHERE ppu.id_usuario = %s AND p.id_estado = 1
            ORDER BY p.nombre ASC
        """, (usuario_id,))
        permisos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(permisos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Verificar si el usuario tiene un permiso específico
@permisos_bp.route('/usuario/verificar/<string:nombre_permiso>', methods=['GET'])
@jwt_required()
def verificar_permiso_usuario(nombre_permiso):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar si el usuario tiene el permiso específico
        cursor.execute("""
            SELECT 
                p.id,
                p.nombre,
                p.id_app,
                p.id_estado
            FROM usuario_dim_permiso p
            JOIN usuario_pivot_permiso_usuario ppu ON p.id = ppu.id_permiso
            WHERE ppu.id_usuario = %s AND p.nombre = %s AND p.id_estado = 1
        """, (usuario_id, nombre_permiso))
        permiso = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if permiso:
            return jsonify({"tiene_permiso": True, "permiso": permiso}), 200
        else:
            return jsonify({"tiene_permiso": False, "permiso": None}), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Verificar múltiples permisos del usuario de una vez
@permisos_bp.route('/usuario/verificar-multiples', methods=['POST'])
@jwt_required()
def verificar_multiples_permisos():
    try:
        data = request.json
        permisos_a_verificar = data.get('permisos', [])
        
        if not permisos_a_verificar:
            return jsonify({"error": "Debe proporcionar una lista de permisos a verificar"}), 400
        
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Crear placeholders para la consulta IN
        placeholders = ','.join(['%s'] * len(permisos_a_verificar))
        
        # Verificar múltiples permisos del usuario
        cursor.execute(f"""
            SELECT 
                p.nombre,
                p.id,
                p.id_app,
                p.id_estado
            FROM usuario_dim_permiso p
            JOIN usuario_pivot_permiso_usuario ppu ON p.id = ppu.id_permiso
            WHERE ppu.id_usuario = %s AND p.nombre IN ({placeholders}) AND p.id_estado = 1
        """, (usuario_id, *permisos_a_verificar))
        
        permisos_encontrados = cursor.fetchall()
        nombres_permisos_encontrados = [p['nombre'] for p in permisos_encontrados]
        
        # Crear respuesta con todos los permisos solicitados
        resultado = {}
        for permiso in permisos_a_verificar:
            resultado[permiso] = {
                "tiene_permiso": permiso in nombres_permisos_encontrados,
                "permiso": next((p for p in permisos_encontrados if p['nombre'] == permiso), None)
            }
        
        cursor.close()
        conn.close()
        
        return jsonify(resultado), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Obtener roles del usuario (permisos agrupados por tipo)
@permisos_bp.route('/usuario/roles', methods=['GET'])
@jwt_required()
def obtener_roles_usuario():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener permisos del usuario agrupados por tipo de rol
        cursor.execute("""
            SELECT 
                p.nombre,
                p.id,
                p.id_app,
                p.id_estado,
                CASE 
                    WHEN p.nombre LIKE '%revisador%' THEN 'revisador'
                    WHEN p.nombre LIKE '%aprobador%' THEN 'aprobador'
                    WHEN p.nombre LIKE '%gestionador%' THEN 'gestionador'
                    WHEN p.nombre LIKE '%admin%' THEN 'administrador'
                    ELSE 'otro'
                END as tipo_rol
            FROM usuario_dim_permiso p
            JOIN usuario_pivot_permiso_usuario ppu ON p.id = ppu.id_permiso
            WHERE ppu.id_usuario = %s AND p.id_estado = 1
            ORDER BY p.nombre ASC
        """, (usuario_id,))
        
        permisos = cursor.fetchall()
        
        # Agrupar por tipo de rol
        roles = {}
        for permiso in permisos:
            tipo_rol = permiso['tipo_rol']
            if tipo_rol not in roles:
                roles[tipo_rol] = []
            roles[tipo_rol].append(permiso)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "roles": roles,
            "permisos_totales": len(permisos),
            "tipos_roles": list(roles.keys())
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Obtener todos los permisos disponibles
@permisos_bp.route('/disponibles', methods=['GET'])
@jwt_required()
def obtener_permisos_disponibles():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener todos los permisos activos
        cursor.execute("""
            SELECT 
                id,
                nombre,
                id_app,
                id_estado
            FROM usuario_dim_permiso
            WHERE id_estado = 1
            ORDER BY nombre ASC
        """)
        permisos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(permisos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Asignar permiso a usuario
@permisos_bp.route('/usuario/asignar', methods=['POST'])
@jwt_required()
def asignar_permiso_usuario():
    try:
        data = request.json
        usuario_id = data.get('id_usuario')
        permiso_id = data.get('id_permiso')
        
        if not usuario_id or not permiso_id:
            return jsonify({"error": "Faltan parámetros requeridos: id_usuario, id_permiso"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que el usuario y permiso existen
        cursor.execute("SELECT id FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404
            
        cursor.execute("SELECT id FROM usuario_dim_permiso WHERE id = %s", (permiso_id,))
        permiso = cursor.fetchone()
        if not permiso:
            return jsonify({"error": "Permiso no encontrado"}), 404
        
        # Verificar que no existe ya la asignación
        cursor.execute("""
            SELECT id FROM usuario_pivot_permiso_usuario 
            WHERE id_usuario = %s AND id_permiso = %s
        """, (usuario_id, permiso_id))
        asignacion_existente = cursor.fetchone()
        
        if asignacion_existente:
            return jsonify({"error": "El usuario ya tiene asignado este permiso"}), 400
        
        # Asignar permiso al usuario
        cursor.execute("""
            INSERT INTO usuario_pivot_permiso_usuario (id_usuario, id_permiso)
            VALUES (%s, %s)
        """, (usuario_id, permiso_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Permiso asignado correctamente al usuario"}), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Remover permiso de usuario
@permisos_bp.route('/usuario/remover', methods=['DELETE'])
@jwt_required()
def remover_permiso_usuario():
    try:
        data = request.json
        usuario_id = data.get('id_usuario')
        permiso_id = data.get('id_permiso')
        
        if not usuario_id or not permiso_id:
            return jsonify({"error": "Faltan parámetros requeridos: id_usuario, id_permiso"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Remover permiso del usuario
        cursor.execute("""
            DELETE FROM usuario_pivot_permiso_usuario 
            WHERE id_usuario = %s AND id_permiso = %s
        """, (usuario_id, permiso_id))
        
        if cursor.rowcount == 0:
            return jsonify({"error": "El usuario no tiene asignado este permiso"}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Permiso removido correctamente del usuario"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Obtener usuarios con sus permisos
@permisos_bp.route('/usuarios/permisos', methods=['GET'])
@jwt_required()
def obtener_usuarios_con_permisos():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener usuarios con sus permisos
        cursor.execute("""
            SELECT 
                u.id,
                u.usuario,
                u.id_colaborador,
                CONCAT(c.nombre, ' ', c.apellido_paterno) as nombre_completo,
                GROUP_CONCAT(p.nombre SEPARATOR ', ') as permisos
            FROM general_dim_usuario u
            LEFT JOIN general_dim_colaborador c ON u.id_colaborador = c.id
            LEFT JOIN usuario_pivot_permiso_usuario ppu ON u.id = ppu.id_usuario
            LEFT JOIN usuario_dim_permiso p ON ppu.id_permiso = p.id AND p.id_estado = 1
            GROUP BY u.id
            ORDER BY u.usuario ASC
        """)
        usuarios = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(usuarios), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
