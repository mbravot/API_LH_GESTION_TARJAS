from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
import uuid
from datetime import datetime

horas_extras_otroscecos_bp = Blueprint('horas_extras_otroscecos_bp', __name__)

# Listar horas extras de otros CECOs
@horas_extras_otroscecos_bp.route('/', methods=['GET'])
@jwt_required()
def listar_horas_extras_otroscecos():
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
        id_cecotipo = request.args.get('id_cecotipo')
        id_ceco = request.args.get('id_ceco')
        
        # Construir query base
        sql = """
            SELECT 
                he.id,
                he.id_colaborador,
                he.fecha,
                he.id_cecotipo,
                he.id_ceco,
                he.cantidad,
                CONCAT(c.nombre, ' ', c.apellido_paterno, 
                       CASE WHEN c.apellido_materno IS NOT NULL THEN CONCAT(' ', c.apellido_materno) ELSE '' END) as nombre_colaborador,
                ct.nombre as nombre_cecotipo,
                ce.nombre as nombre_ceco
            FROM tarja_fact_he_otroceco he
            INNER JOIN general_dim_colaborador c ON he.id_colaborador = c.id
            INNER JOIN general_dim_cecotipo ct ON he.id_cecotipo = ct.id
            INNER JOIN general_dim_ceco ce ON he.id_ceco = ce.id
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
        
        if id_cecotipo:
            sql += " AND he.id_cecotipo = %s"
            params.append(id_cecotipo)
        
        if id_ceco:
            sql += " AND he.id_ceco = %s"
            params.append(id_ceco)
        
        sql += " ORDER BY he.fecha DESC, c.nombre ASC"
        
        cursor.execute(sql, tuple(params))
        horas_extras = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(horas_extras), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener horas extras de otros CECOs por ID
@horas_extras_otroscecos_bp.route('/<string:he_id>', methods=['GET'])
@jwt_required()
def obtener_horas_extras_otroscecos(he_id):
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
        
        # Obtener horas extras específicas
        cursor.execute("""
            SELECT 
                he.id,
                he.id_colaborador,
                he.fecha,
                he.id_cecotipo,
                he.id_ceco,
                he.cantidad,
                CONCAT(c.nombre, ' ', c.apellido_paterno, 
                       CASE WHEN c.apellido_materno IS NOT NULL THEN CONCAT(' ', c.apellido_materno) ELSE '' END) as nombre_colaborador,
                ct.nombre as nombre_cecotipo,
                ce.nombre as nombre_ceco
            FROM tarja_fact_he_otroceco he
            INNER JOIN general_dim_colaborador c ON he.id_colaborador = c.id
            INNER JOIN general_dim_cecotipo ct ON he.id_cecotipo = ct.id
            INNER JOIN general_dim_ceco ce ON he.id_ceco = ce.id
            WHERE he.id = %s AND c.id_sucursal = %s
        """, (he_id, id_sucursal))
        
        horas_extras = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not horas_extras:
            return jsonify({"error": "Horas extras no encontradas"}), 404
        
        return jsonify(horas_extras), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Crear horas extras de otros CECOs
@horas_extras_otroscecos_bp.route('/', methods=['POST'])
@jwt_required()
def crear_horas_extras_otroscecos():
    try:
        data = request.json
        usuario_id = get_jwt_identity()
        
        # Validar campos requeridos
        campos_requeridos = ['id_colaborador', 'fecha', 'id_cecotipo', 'id_ceco', 'cantidad']
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
        
        # Verificar que el tipo de CECO existe
        cursor.execute("""
            SELECT id FROM general_dim_cecotipo 
            WHERE id = %s
        """, (data['id_cecotipo'],))
        
        if not cursor.fetchone():
            return jsonify({"error": "Tipo de CECO no encontrado"}), 404
        
        # Verificar que el CECO existe
        cursor.execute("""
            SELECT id FROM general_dim_ceco 
            WHERE id = %s
        """, (data['id_ceco'],))
        
        if not cursor.fetchone():
            return jsonify({"error": "CECO no encontrado"}), 404
        
        # Generar ID único
        he_id = str(uuid.uuid4())
        
        # Crear horas extras
        cursor.execute("""
            INSERT INTO tarja_fact_he_otroceco (
                id, id_colaborador, fecha, id_cecotipo, id_ceco, cantidad
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            he_id,
            data['id_colaborador'],
            data['fecha'],
            data['id_cecotipo'],
            data['id_ceco'],
            cantidad
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Horas extras creadas correctamente", "id": he_id}), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar horas extras de otros CECOs
@horas_extras_otroscecos_bp.route('/<string:he_id>', methods=['PUT'])
@jwt_required()
def editar_horas_extras_otroscecos(he_id):
    try:
        data = request.json
        usuario_id = get_jwt_identity()
        
        # Validar campos requeridos
        campos_requeridos = ['id_colaborador', 'fecha', 'id_cecotipo', 'id_ceco', 'cantidad']
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
        
        # Verificar que las horas extras existen y pertenecen a la sucursal
        cursor.execute("""
            SELECT he.id FROM tarja_fact_he_otroceco he
            INNER JOIN general_dim_colaborador c ON he.id_colaborador = c.id
            WHERE he.id = %s AND c.id_sucursal = %s
        """, (he_id, id_sucursal))
        
        if not cursor.fetchone():
            return jsonify({"error": "Horas extras no encontradas"}), 404
        
        # Verificar que el colaborador pertenece a la sucursal
        cursor.execute("""
            SELECT id FROM general_dim_colaborador 
            WHERE id = %s AND id_sucursal = %s
        """, (data['id_colaborador'], id_sucursal))
        
        if not cursor.fetchone():
            return jsonify({"error": "Colaborador no encontrado o no pertenece a tu sucursal"}), 404
        
        # Verificar que el tipo de CECO existe
        cursor.execute("""
            SELECT id FROM general_dim_cecotipo 
            WHERE id = %s
        """, (data['id_cecotipo'],))
        
        if not cursor.fetchone():
            return jsonify({"error": "Tipo de CECO no encontrado"}), 404
        
        # Verificar que el CECO existe
        cursor.execute("""
            SELECT id FROM general_dim_ceco 
            WHERE id = %s
        """, (data['id_ceco'],))
        
        if not cursor.fetchone():
            return jsonify({"error": "CECO no encontrado"}), 404
        
        # Actualizar horas extras
        cursor.execute("""
            UPDATE tarja_fact_he_otroceco 
            SET id_colaborador = %s, fecha = %s, id_cecotipo = %s, id_ceco = %s, cantidad = %s
            WHERE id = %s
        """, (
            data['id_colaborador'],
            data['fecha'],
            data['id_cecotipo'],
            data['id_ceco'],
            cantidad,
            he_id
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Horas extras actualizadas correctamente"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Eliminar horas extras de otros CECOs
@horas_extras_otroscecos_bp.route('/<string:he_id>', methods=['DELETE'])
@jwt_required()
def eliminar_horas_extras_otroscecos(he_id):
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
        
        # Verificar que las horas extras existen y pertenecen a la sucursal
        cursor.execute("""
            SELECT he.id FROM tarja_fact_he_otroceco he
            INNER JOIN general_dim_colaborador c ON he.id_colaborador = c.id
            WHERE he.id = %s AND c.id_sucursal = %s
        """, (he_id, id_sucursal))
        
        if not cursor.fetchone():
            return jsonify({"error": "Horas extras no encontradas"}), 404
        
        # Eliminar horas extras
        cursor.execute("DELETE FROM tarja_fact_he_otroceco WHERE id = %s", (he_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Horas extras eliminadas correctamente"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener opciones para crear/editar (tipos de CECO y CECOs)
# Obtener tipos de CECO
@horas_extras_otroscecos_bp.route('/tipos-ceco', methods=['GET'])
@jwt_required()
def obtener_tipos_ceco():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener tipos de CECO
        cursor.execute("SELECT id, nombre FROM general_dim_cecotipo ORDER BY nombre")
        tipos_ceco = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(tipos_ceco), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener CECOs por tipo
@horas_extras_otroscecos_bp.route('/cecos-por-tipo/<int:id_tipo_ceco>', methods=['GET'])
@jwt_required()
def obtener_cecos_por_tipo(id_tipo_ceco):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener la sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        
        if not usuario or usuario['id_sucursalactiva'] is None:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        id_sucursal = usuario['id_sucursalactiva']
        
        # Obtener CECOs del tipo seleccionado y de la sucursal del usuario
        cursor.execute("""
            SELECT id, nombre 
            FROM general_dim_ceco 
            WHERE id_cecotipo = %s AND id_sucursal = %s AND id_estado = 1
            ORDER BY nombre
        """, (id_tipo_ceco, id_sucursal))
        cecos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(cecos), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@horas_extras_otroscecos_bp.route('/opciones', methods=['GET'])
@jwt_required()
def obtener_opciones_horas_extras_otroscecos():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener tipos de CECO
        cursor.execute("SELECT id, nombre FROM general_dim_cecotipo ORDER BY nombre")
        tipos_ceco = cursor.fetchall()
        
        # Obtener CECOs
        cursor.execute("SELECT id, nombre FROM general_dim_ceco ORDER BY nombre")
        cecos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'tipos_ceco': tipos_ceco,
            'cecos': cecos
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
