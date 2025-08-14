from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
import uuid
from datetime import datetime

licencias_bp = Blueprint('licencias_bp', __name__)

# Listar licencias médicas de colaboradores (por sucursal activa del usuario)
@licencias_bp.route('', methods=['GET'])
@jwt_required()
def listar_licencias():
    try:
        usuario_id = get_jwt_identity()
        id_colaborador = request.args.get('id_colaborador')  # Filtro opcional por colaborador
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        id_sucursal = usuario['id_sucursalactiva']
        
        # Construir query base
        base_query = """
            SELECT 
                l.id,
                l.id_colaborador,
                l.fecha_inicio,
                l.fecha_fin,
                c.nombre as nombre_colaborador,
                c.apellido_paterno,
                c.apellido_materno,
                c.id_sucursal
            FROM tarja_fact_licenciamedica l
            INNER JOIN general_dim_colaborador c ON l.id_colaborador = c.id
            WHERE c.id_sucursal = %s
        """
        params = [id_sucursal]
        
        # Agregar filtro por colaborador si se especifica
        if id_colaborador:
            base_query += " AND l.id_colaborador = %s"
            params.append(id_colaborador)
        
        base_query += " ORDER BY l.fecha_inicio DESC"
        
        cursor.execute(base_query, tuple(params))
        licencias = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(licencias), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener licencia por ID
@licencias_bp.route('/<int:licencia_id>', methods=['GET'])
@jwt_required()
def obtener_licencia_por_id(licencia_id):
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
        
        # Obtener licencia con información del colaborador
        cursor.execute("""
            SELECT 
                l.id,
                l.id_colaborador,
                l.fecha_inicio,
                l.fecha_fin,
                c.nombre as nombre_colaborador,
                c.apellido_paterno,
                c.apellido_materno,
                c.id_sucursal
            FROM tarja_fact_licenciamedica l
            INNER JOIN general_dim_colaborador c ON l.id_colaborador = c.id
            WHERE l.id = %s AND c.id_sucursal = %s
        """, (licencia_id, id_sucursal))
        
        licencia = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not licencia:
            return jsonify({"error": "Licencia no encontrada"}), 404
            
        return jsonify(licencia), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Crear licencia médica
@licencias_bp.route('/', methods=['POST'])
@jwt_required()
def crear_licencia():
    try:
        data = request.json
        usuario_id = get_jwt_identity()
        
        # Validar campos requeridos
        if not data.get('id_colaborador') or not data.get('fecha_inicio') or not data.get('fecha_fin'):
            return jsonify({"error": "Faltan campos requeridos: id_colaborador, fecha_inicio, fecha_fin"}), 400
        
        # Validar formato de fechas
        try:
            fecha_inicio = datetime.strptime(data['fecha_inicio'], '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(data['fecha_fin'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}), 400
        
        # Validar que fecha_fin sea posterior a fecha_inicio
        if fecha_fin <= fecha_inicio:
            return jsonify({"error": "La fecha de fin debe ser posterior a la fecha de inicio"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        id_sucursal = usuario['id_sucursalactiva']
        
        # Verificar que el colaborador existe y pertenece a la sucursal
        cursor.execute("""
            SELECT id FROM general_dim_colaborador 
            WHERE id = %s AND id_sucursal = %s
        """, (data['id_colaborador'], id_sucursal))
        
        colaborador = cursor.fetchone()
        if not colaborador:
            return jsonify({"error": "Colaborador no encontrado o no pertenece a la sucursal"}), 404
        
        # Verificar que no haya solapamiento de fechas
        cursor.execute("""
            SELECT id FROM tarja_fact_licenciamedica 
            WHERE id_colaborador = %s AND (
                (fecha_inicio <= %s AND fecha_fin >= %s) OR
                (fecha_inicio <= %s AND fecha_fin >= %s) OR
                (fecha_inicio >= %s AND fecha_fin <= %s)
            )
        """, (data['id_colaborador'], fecha_inicio, fecha_inicio, fecha_fin, fecha_fin, fecha_inicio, fecha_fin))
        
        if cursor.fetchone():
            return jsonify({"error": "Ya existe un período de licencia médica que se solapa con las fechas especificadas"}), 400
        
        # Crear licencia
        sql = """
            INSERT INTO tarja_fact_licenciamedica (id_colaborador, fecha_inicio, fecha_fin)
            VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (data['id_colaborador'], fecha_inicio, fecha_fin))
        
        licencia_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Licencia médica creada correctamente", 
            "id": licencia_id
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar licencia médica
@licencias_bp.route('/<int:licencia_id>', methods=['PUT'])
@jwt_required()
def editar_licencia(licencia_id):
    try:
        data = request.json
        usuario_id = get_jwt_identity()
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        id_sucursal = usuario['id_sucursalactiva']
        
        # Obtener licencia actual
        cursor.execute("""
            SELECT l.*, c.id_sucursal
            FROM tarja_fact_licenciamedica l
            INNER JOIN general_dim_colaborador c ON l.id_colaborador = c.id
            WHERE l.id = %s AND c.id_sucursal = %s
        """, (licencia_id, id_sucursal))
        
        licencia_actual = cursor.fetchone()
        if not licencia_actual:
            return jsonify({"error": "Licencia no encontrada"}), 404
        
        # Validar y procesar fechas si se proporcionan
        fecha_inicio = licencia_actual['fecha_inicio']
        fecha_fin = licencia_actual['fecha_fin']
        
        if 'fecha_inicio' in data:
            try:
                fecha_inicio = datetime.strptime(data['fecha_inicio'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({"error": "Formato de fecha_inicio inválido. Use YYYY-MM-DD"}), 400
        
        if 'fecha_fin' in data:
            try:
                fecha_fin = datetime.strptime(data['fecha_fin'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({"error": "Formato de fecha_fin inválido. Use YYYY-MM-DD"}), 400
        
        # Validar que fecha_fin sea posterior a fecha_inicio
        if fecha_fin <= fecha_inicio:
            return jsonify({"error": "La fecha de fin debe ser posterior a la fecha de inicio"}), 400
        
        # Verificar que no haya solapamiento de fechas (excluyendo la licencia actual)
        cursor.execute("""
            SELECT id FROM tarja_fact_licenciamedica 
            WHERE id_colaborador = %s AND id != %s AND (
                (fecha_inicio <= %s AND fecha_fin >= %s) OR
                (fecha_inicio <= %s AND fecha_fin >= %s) OR
                (fecha_inicio >= %s AND fecha_fin <= %s)
            )
        """, (licencia_actual['id_colaborador'], licencia_id, fecha_inicio, fecha_inicio, fecha_fin, fecha_fin, fecha_inicio, fecha_fin))
        
        if cursor.fetchone():
            return jsonify({"error": "Ya existe un período de licencia médica que se solapa con las fechas especificadas"}), 400
        
        # Actualizar licencia
        sql = """
            UPDATE tarja_fact_licenciamedica
            SET fecha_inicio = %s, fecha_fin = %s
            WHERE id = %s
        """
        cursor.execute(sql, (fecha_inicio, fecha_fin, licencia_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Licencia médica actualizada correctamente"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Eliminar licencia médica
@licencias_bp.route('/<int:licencia_id>', methods=['DELETE'])
@jwt_required()
def eliminar_licencia(licencia_id):
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
        
        # Verificar que la licencia existe y pertenece a un colaborador de la sucursal
        cursor.execute("""
            SELECT l.id
            FROM tarja_fact_licenciamedica l
            INNER JOIN general_dim_colaborador c ON l.id_colaborador = c.id
            WHERE l.id = %s AND c.id_sucursal = %s
        """, (licencia_id, id_sucursal))
        
        if not cursor.fetchone():
            return jsonify({"error": "Licencia no encontrada"}), 404
        
        # Eliminar licencia
        cursor.execute("DELETE FROM tarja_fact_licenciamedica WHERE id = %s", (licencia_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Licencia médica eliminada correctamente"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener licencias de un colaborador específico
@licencias_bp.route('/colaborador/<string:id_colaborador>', methods=['GET'])
@jwt_required()
def obtener_licencias_colaborador(id_colaborador):
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
        
        # Obtener licencias del colaborador
        cursor.execute("""
            SELECT 
                l.id,
                l.id_colaborador,
                l.fecha_inicio,
                l.fecha_fin,
                c.nombre as nombre_colaborador,
                c.apellido_paterno,
                c.apellido_materno,
                c.id_sucursal
            FROM tarja_fact_licenciamedica l
            INNER JOIN general_dim_colaborador c ON l.id_colaborador = c.id
            WHERE l.id_colaborador = %s AND c.id_sucursal = %s
            ORDER BY l.fecha_inicio DESC
        """, (id_colaborador, id_sucursal))
        
        licencias = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(licencias), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
