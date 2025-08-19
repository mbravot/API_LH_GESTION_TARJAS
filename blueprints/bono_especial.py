from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
import uuid
from datetime import datetime

bono_especial_bp = Blueprint('bono_especial_bp', __name__)

# Listar bonos especiales (horas extras sobrantes)
@bono_especial_bp.route('/', methods=['GET'])
@jwt_required()
def listar_bonos_especiales():
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
        
        # Parámetros de filtrado
        id_colaborador = request.args.get('id_colaborador')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        # Construir query base
        sql = """
            SELECT 
                he.id,
                he.id_colaborador,
                he.fecha,
                he.cantidad,
                CONCAT(c.nombre, ' ', c.apellido_paterno, 
                       CASE WHEN c.apellido_materno IS NOT NULL THEN CONCAT(' ', c.apellido_materno) ELSE '' END) as nombre_colaborador
            FROM tarja_fact_he_sobrante he
            INNER JOIN general_dim_colaborador c ON he.id_colaborador = c.id
            WHERE c.id_sucursal = %s
        """
        params = [id_sucursal]
        
        # Agregar filtros
        if id_colaborador:
            sql += " AND he.id_colaborador = %s"
            params.append(id_colaborador)
        
        if fecha_inicio:
            sql += " AND he.fecha >= %s"
            params.append(fecha_inicio)
        
        if fecha_fin:
            sql += " AND he.fecha <= %s"
            params.append(fecha_fin)
        
        sql += " ORDER BY he.fecha DESC, c.nombre ASC"
        
        cursor.execute(sql, tuple(params))
        bonos_especiales = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(bonos_especiales), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener bono especial por ID
@bono_especial_bp.route('/<string:bono_id>', methods=['GET'])
@jwt_required()
def obtener_bono_especial(bono_id):
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
        
        # Obtener bono especial específico
        cursor.execute("""
            SELECT 
                he.id,
                he.id_colaborador,
                he.fecha,
                he.cantidad,
                CONCAT(c.nombre, ' ', c.apellido_paterno, 
                       CASE WHEN c.apellido_materno IS NOT NULL THEN CONCAT(' ', c.apellido_materno) ELSE '' END) as nombre_colaborador
            FROM tarja_fact_he_sobrante he
            INNER JOIN general_dim_colaborador c ON he.id_colaborador = c.id
            WHERE he.id = %s AND c.id_sucursal = %s
        """, (bono_id, id_sucursal))
        
        bono_especial = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not bono_especial:
            return jsonify({"error": "Bono especial no encontrado"}), 404
        
        return jsonify(bono_especial), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Crear bono especial
@bono_especial_bp.route('/', methods=['POST'])
@jwt_required()
def crear_bono_especial():
    try:
        data = request.json
        usuario_id = get_jwt_identity()
        
        # Validar campos requeridos
        campos_requeridos = ['id_colaborador', 'fecha', 'cantidad']
        for campo in campos_requeridos:
            if not data.get(campo):
                return jsonify({"error": f"Campo requerido faltante: {campo}"}), 400
        
        # Validar cantidad
        cantidad = data['cantidad']
        if not isinstance(cantidad, (int, float)) or cantidad <= 0:
            return jsonify({"error": "cantidad debe ser un número positivo"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        id_sucursal = usuario['id_sucursalactiva']
        
        # Verificar que el colaborador pertenece a la sucursal
        cursor.execute("""
            SELECT id FROM general_dim_colaborador 
            WHERE id = %s AND id_sucursal = %s
        """, (data['id_colaborador'], id_sucursal))
        
        if not cursor.fetchone():
            return jsonify({"error": "Colaborador no encontrado o no pertenece a tu sucursal"}), 404
        
        # Generar ID único
        bono_id = str(uuid.uuid4())
        
        # Crear bono especial
        cursor.execute("""
            INSERT INTO tarja_fact_he_sobrante (
                id, id_colaborador, fecha, cantidad
            ) VALUES (%s, %s, %s, %s)
        """, (
            bono_id,
            data['id_colaborador'],
            data['fecha'],
            cantidad
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Bono especial creado correctamente", "id": bono_id}), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar bono especial
@bono_especial_bp.route('/<string:bono_id>', methods=['PUT'])
@jwt_required()
def editar_bono_especial(bono_id):
    try:
        data = request.json
        usuario_id = get_jwt_identity()
        
        # Validar campos requeridos
        campos_requeridos = ['id_colaborador', 'fecha', 'cantidad']
        for campo in campos_requeridos:
            if not data.get(campo):
                return jsonify({"error": f"Campo requerido faltante: {campo}"}), 400
        
        # Validar cantidad
        cantidad = data['cantidad']
        if not isinstance(cantidad, (int, float)) or cantidad <= 0:
            return jsonify({"error": "cantidad debe ser un número positivo"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        id_sucursal = usuario['id_sucursalactiva']
        
        # Verificar que el bono especial existe y pertenece a la sucursal
        cursor.execute("""
            SELECT he.id FROM tarja_fact_he_sobrante he
            INNER JOIN general_dim_colaborador c ON he.id_colaborador = c.id
            WHERE he.id = %s AND c.id_sucursal = %s
        """, (bono_id, id_sucursal))
        
        if not cursor.fetchone():
            return jsonify({"error": "Bono especial no encontrado"}), 404
        
        # Verificar que el colaborador pertenece a la sucursal
        cursor.execute("""
            SELECT id FROM general_dim_colaborador 
            WHERE id = %s AND id_sucursal = %s
        """, (data['id_colaborador'], id_sucursal))
        
        if not cursor.fetchone():
            return jsonify({"error": "Colaborador no encontrado o no pertenece a tu sucursal"}), 404
        
        # Actualizar bono especial
        cursor.execute("""
            UPDATE tarja_fact_he_sobrante 
            SET id_colaborador = %s, fecha = %s, cantidad = %s
            WHERE id = %s
        """, (
            data['id_colaborador'],
            data['fecha'],
            cantidad,
            bono_id
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Bono especial actualizado correctamente"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Eliminar bono especial
@bono_especial_bp.route('/<string:bono_id>', methods=['DELETE'])
@jwt_required()
def eliminar_bono_especial(bono_id):
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
        
        # Verificar que el bono especial existe y pertenece a la sucursal
        cursor.execute("""
            SELECT he.id FROM tarja_fact_he_sobrante he
            INNER JOIN general_dim_colaborador c ON he.id_colaborador = c.id
            WHERE he.id = %s AND c.id_sucursal = %s
        """, (bono_id, id_sucursal))
        
        if not cursor.fetchone():
            return jsonify({"error": "Bono especial no encontrado"}), 404
        
        # Eliminar bono especial
        cursor.execute("DELETE FROM tarja_fact_he_sobrante WHERE id = %s", (bono_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Bono especial eliminado correctamente"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener resumen de bonos especiales por colaborador
@bono_especial_bp.route('/resumen-colaborador', methods=['GET'])
@jwt_required()
def obtener_resumen_bonos_especiales_colaborador():
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
        
        # Parámetros de filtrado
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        # Construir query para obtener resumen agrupado por colaborador
        sql = """
            SELECT 
                c.id as id_colaborador,
                CONCAT(c.nombre, ' ', c.apellido_paterno, 
                       CASE WHEN c.apellido_materno IS NOT NULL THEN CONCAT(' ', c.apellido_materno) ELSE '' END) as nombre_colaborador,
                COUNT(he.id) as cantidad_bonos,
                SUM(he.cantidad) as total_horas_sobrantes,
                MIN(he.fecha) as fecha_inicio,
                MAX(he.fecha) as fecha_fin
            FROM general_dim_colaborador c
            LEFT JOIN tarja_fact_he_sobrante he ON c.id = he.id_colaborador
            WHERE c.id_sucursal = %s
        """
        params = [id_sucursal]
        
        # Agregar filtros de fecha
        if fecha_inicio:
            sql += " AND he.fecha >= %s"
            params.append(fecha_inicio)
        
        if fecha_fin:
            sql += " AND he.fecha <= %s"
            params.append(fecha_fin)
        
        sql += " GROUP BY c.id, c.nombre, c.apellido_paterno, c.apellido_materno ORDER BY c.nombre ASC"
        
        cursor.execute(sql, tuple(params))
        resumen = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(resumen), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
