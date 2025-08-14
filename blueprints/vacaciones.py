from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
import uuid
from datetime import datetime

vacaciones_bp = Blueprint('vacaciones_bp', __name__)

# Listar vacaciones de colaboradores (por sucursal activa del usuario)
@vacaciones_bp.route('', methods=['GET'])
@jwt_required()
def listar_vacaciones():
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
                v.id,
                v.id_colaborador,
                v.fecha_inicio,
                v.fecha_fin,
                c.nombre as nombre_colaborador,
                c.apellido_paterno,
                c.apellido_materno,
                c.id_sucursal
            FROM tarja_fact_vacaciones v
            INNER JOIN general_dim_colaborador c ON v.id_colaborador = c.id
            WHERE c.id_sucursal = %s
        """
        params = [id_sucursal]
        
        # Agregar filtro por colaborador si se especifica
        if id_colaborador:
            base_query += " AND v.id_colaborador = %s"
            params.append(id_colaborador)
        
        base_query += " ORDER BY v.fecha_inicio DESC"
        
        cursor.execute(base_query, tuple(params))
        vacaciones = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(vacaciones), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener vacaciones por ID
@vacaciones_bp.route('/<int:vacacion_id>', methods=['GET'])
@jwt_required()
def obtener_vacacion_por_id(vacacion_id):
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
        
        # Obtener vacación con información del colaborador
        cursor.execute("""
            SELECT 
                v.id,
                v.id_colaborador,
                v.fecha_inicio,
                v.fecha_fin,
                c.nombre as nombre_colaborador,
                c.apellido_paterno,
                c.apellido_materno,
                c.id_sucursal
            FROM tarja_fact_vacaciones v
            INNER JOIN general_dim_colaborador c ON v.id_colaborador = c.id
            WHERE v.id = %s AND c.id_sucursal = %s
        """, (vacacion_id, id_sucursal))
        
        vacacion = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not vacacion:
            return jsonify({"error": "Vacación no encontrada"}), 404
            
        return jsonify(vacacion), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Crear vacación
@vacaciones_bp.route('/', methods=['POST'])
@jwt_required()
def crear_vacacion():
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
            SELECT id FROM tarja_fact_vacaciones 
            WHERE id_colaborador = %s AND (
                (fecha_inicio <= %s AND fecha_fin >= %s) OR
                (fecha_inicio <= %s AND fecha_fin >= %s) OR
                (fecha_inicio >= %s AND fecha_fin <= %s)
            )
        """, (data['id_colaborador'], fecha_inicio, fecha_inicio, fecha_fin, fecha_fin, fecha_inicio, fecha_fin))
        
        if cursor.fetchone():
            return jsonify({"error": "Ya existe un período de vacaciones que se solapa con las fechas especificadas"}), 400
        
        # Crear vacación
        sql = """
            INSERT INTO tarja_fact_vacaciones (id_colaborador, fecha_inicio, fecha_fin)
            VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (data['id_colaborador'], fecha_inicio, fecha_fin))
        
        vacacion_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Vacación creada correctamente", 
            "id": vacacion_id
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar vacación
@vacaciones_bp.route('/<int:vacacion_id>', methods=['PUT'])
@jwt_required()
def editar_vacacion(vacacion_id):
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
        
        # Obtener vacación actual
        cursor.execute("""
            SELECT v.*, c.id_sucursal
            FROM tarja_fact_vacaciones v
            INNER JOIN general_dim_colaborador c ON v.id_colaborador = c.id
            WHERE v.id = %s AND c.id_sucursal = %s
        """, (vacacion_id, id_sucursal))
        
        vacacion_actual = cursor.fetchone()
        if not vacacion_actual:
            return jsonify({"error": "Vacación no encontrada"}), 404
        
        # Validar y procesar fechas si se proporcionan
        fecha_inicio = vacacion_actual['fecha_inicio']
        fecha_fin = vacacion_actual['fecha_fin']
        
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
        
        # Verificar que no haya solapamiento de fechas (excluyendo la vacación actual)
        cursor.execute("""
            SELECT id FROM tarja_fact_vacaciones 
            WHERE id_colaborador = %s AND id != %s AND (
                (fecha_inicio <= %s AND fecha_fin >= %s) OR
                (fecha_inicio <= %s AND fecha_fin >= %s) OR
                (fecha_inicio >= %s AND fecha_fin <= %s)
            )
        """, (vacacion_actual['id_colaborador'], vacacion_id, fecha_inicio, fecha_inicio, fecha_fin, fecha_fin, fecha_inicio, fecha_fin))
        
        if cursor.fetchone():
            return jsonify({"error": "Ya existe un período de vacaciones que se solapa con las fechas especificadas"}), 400
        
        # Actualizar vacación
        sql = """
            UPDATE tarja_fact_vacaciones
            SET fecha_inicio = %s, fecha_fin = %s
            WHERE id = %s
        """
        cursor.execute(sql, (fecha_inicio, fecha_fin, vacacion_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Vacación actualizada correctamente"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Eliminar vacación
@vacaciones_bp.route('/<int:vacacion_id>', methods=['DELETE'])
@jwt_required()
def eliminar_vacacion(vacacion_id):
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
        
        # Verificar que la vacación existe y pertenece a un colaborador de la sucursal
        cursor.execute("""
            SELECT v.id
            FROM tarja_fact_vacaciones v
            INNER JOIN general_dim_colaborador c ON v.id_colaborador = c.id
            WHERE v.id = %s AND c.id_sucursal = %s
        """, (vacacion_id, id_sucursal))
        
        if not cursor.fetchone():
            return jsonify({"error": "Vacación no encontrada"}), 404
        
        # Eliminar vacación
        cursor.execute("DELETE FROM tarja_fact_vacaciones WHERE id = %s", (vacacion_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Vacación eliminada correctamente"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener vacaciones de un colaborador específico
@vacaciones_bp.route('/colaborador/<string:id_colaborador>', methods=['GET'])
@jwt_required()
def obtener_vacaciones_colaborador(id_colaborador):
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
        
        # Obtener vacaciones del colaborador
        cursor.execute("""
            SELECT 
                v.id,
                v.id_colaborador,
                v.fecha_inicio,
                v.fecha_fin,
                c.nombre as nombre_colaborador,
                c.apellido_paterno,
                c.apellido_materno,
                c.id_sucursal
            FROM tarja_fact_vacaciones v
            INNER JOIN general_dim_colaborador c ON v.id_colaborador = c.id
            WHERE v.id_colaborador = %s AND c.id_sucursal = %s
            ORDER BY v.fecha_inicio DESC
        """, (id_colaborador, id_sucursal))
        
        vacaciones = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(vacaciones), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
