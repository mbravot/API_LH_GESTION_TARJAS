from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
from datetime import datetime, date
import uuid

permisos_ausencia_bp = Blueprint('permisos_ausencia_bp', __name__)

def format_fecha(fecha):
    if isinstance(fecha, (date, datetime)):
        return fecha.strftime('%Y-%m-%d')
    return fecha

# Listar permisos dia(solo de la sucursal activa del usuario)
@permisos_ausencia_bp.route('', methods=['GET'])
@jwt_required()
def listar_permisos():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        id_sucursal = usuario['id_sucursalactiva']
        # Listar permisos de colaboradores de la sucursal y del usuario autenticado
        cursor.execute("""
            SELECT p.*, t.nombre AS tipo_permiso, c.nombre AS nombre_colaborador, c.apellido_paterno, c.apellido_materno, e.nombre AS estado_permiso
            FROM tarja_fact_permiso p
            JOIN tarja_dim_permisotipo t ON p.id_tipopermiso = t.id
            JOIN general_dim_colaborador c ON p.id_colaborador = c.id
            JOIN tarja_dim_permisoestado e ON p.id_estadopermiso = e.id
            WHERE c.id_sucursal = %s AND p.id_usuario = %s
            ORDER BY p.fecha DESC, p.timestamp DESC
        """, (id_sucursal, usuario_id))
        permisos = cursor.fetchall()
        cursor.close()
        conn.close()
        # Formatear fechas
        for permiso in permisos:
            if 'fecha' in permiso and permiso['fecha']:
                permiso['fecha'] = format_fecha(permiso['fecha'])
            if 'timestamp' in permiso and permiso['timestamp']:
                permiso['timestamp'] = format_fecha(permiso['timestamp'])
        return jsonify(permisos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Crear permiso dia
@permisos_ausencia_bp.route('/', methods=['POST'])
@jwt_required()
def crear_permiso():
    try:
        data = request.json
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Generar id UUID
        permiso_id = str(uuid.uuid4())
        sql = """
            INSERT INTO tarja_fact_permiso (
                id, id_usuario, timestamp, fecha, id_tipopermiso, id_colaborador, horas, id_estadopermiso
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        now = datetime.now()
        cursor.execute(sql, (
            permiso_id,
            usuario_id,
            now,
            data['fecha'],
            data['id_tipopermiso'],
            data['id_colaborador'],
            data['horas'],
            data['id_estadopermiso']
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Permiso creado correctamente", "id": permiso_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar permiso dia
@permisos_ausencia_bp.route('/<string:permiso_id>', methods=['PUT'])
@jwt_required()
def editar_permiso(permiso_id):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Verificar que el permiso existe
        cursor.execute("SELECT * FROM tarja_fact_permiso WHERE id = %s", (permiso_id,))
        permiso = cursor.fetchone()
        if not permiso:
            return jsonify({"error": "Permiso no encontrado"}), 404
        # Actualizar campos editables
        sql = """
            UPDATE tarja_fact_permiso
            SET fecha = %s, id_tipopermiso = %s, id_colaborador = %s, horas = %s, id_estadopermiso = %s
            WHERE id = %s
        """
        cursor.execute(sql, (
            data.get('fecha', permiso['fecha']),
            data.get('id_tipopermiso', permiso['id_tipopermiso']),
            data.get('id_colaborador', permiso['id_colaborador']),
            data.get('horas', permiso['horas']),
            data.get('id_estadopermiso', permiso['id_estadopermiso']),
            permiso_id
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Permiso actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Eliminar permiso día 
@permisos_ausencia_bp.route('/<string:permiso_id>', methods=['DELETE'])
@jwt_required()
def eliminar_permiso(permiso_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("DELETE FROM tarja_fact_permiso WHERE id = %s", (permiso_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Permiso eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener tipos de permisos dia
@permisos_ausencia_bp.route('/tipos', methods=['GET'])
@jwt_required()
def obtener_tipos_permiso():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre FROM tarja_dim_permisotipo ORDER BY nombre ASC")
        tipos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(tipos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener permiso día por id
@permisos_ausencia_bp.route('/<string:permiso_id>', methods=['GET'])
@jwt_required()
def obtener_permiso_por_id(permiso_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.*, t.nombre AS tipo_permiso, c.nombre AS nombre_colaborador, c.apellido_paterno, c.apellido_materno, e.nombre AS estado_permiso
            FROM tarja_fact_permiso p
            JOIN tarja_dim_permisotipo t ON p.id_tipopermiso = t.id
            JOIN general_dim_colaborador c ON p.id_colaborador = c.id
            JOIN tarja_dim_permisoestado e ON p.id_estadopermiso = e.id
            WHERE p.id = %s
        """, (permiso_id,))
        permiso = cursor.fetchone()
        cursor.close()
        conn.close()
        if not permiso:
            return jsonify({"error": "Permiso no encontrado"}), 404
        if 'fecha' in permiso and permiso['fecha']:
            permiso['fecha'] = format_fecha(permiso['fecha'])
        if 'timestamp' in permiso and permiso['timestamp']:
            permiso['timestamp'] = format_fecha(permiso['timestamp'])
        return jsonify(permiso), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500 