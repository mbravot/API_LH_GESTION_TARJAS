from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
from utils.validar_rut import validar_rut
import uuid


trabajadores_bp = Blueprint('trabajadores_bp', __name__)

# Obtener trabajadores
@trabajadores_bp.route('', methods=['GET'])  
@jwt_required()
def obtener_trabajadores():
    try:
        id_contratista = request.args.get('id_contratista')
        id_sucursal = request.args.get('id_sucursal')
        usuario_id = get_jwt_identity()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Si no se pasa id_sucursal, usar la sucursal activa del usuario
        if not id_sucursal:
            cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
            usuario = cursor.fetchone()
            if not usuario or usuario['id_sucursalactiva'] is None:
                return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
            id_sucursal = usuario['id_sucursalactiva']

        base_query = """
            SELECT t.id, t.rut, t.codigo_verificador, t.nombre, t.apellido_paterno, t.apellido_materno,
                   t.id_contratista, t.id_porcentaje, t.id_estado, t.id_sucursal_activa,
                   c.nombre as nombre_contratista, p.porcentaje, s.nombre as nombre_sucursal
            FROM general_dim_trabajador t
            LEFT JOIN general_dim_contratista c ON t.id_contratista = c.id
            LEFT JOIN general_dim_porcentajecontratista p ON t.id_porcentaje = p.id
            LEFT JOIN general_dim_sucursal s ON t.id_sucursal_activa = s.id
            WHERE t.id_sucursal_activa = %s
        """
        params = [id_sucursal]

        if id_contratista:
            base_query += " AND t.id_contratista = %s"
            params.append(id_contratista)

        base_query += " ORDER BY t.nombre, t.apellido_paterno, t.apellido_materno ASC"

        cursor.execute(base_query, tuple(params))
        trabajadores = cursor.fetchall()

        cursor.close()
        conn.close()
        return jsonify(trabajadores), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 📌 Crear trabajador
@trabajadores_bp.route('/', methods=['POST'])
@jwt_required()
def crear_trabajador():
    try:
        data = request.json
        usuario_id = get_jwt_identity()

        # Validar RUT solo si ambos campos están presentes y no vacíos
        rut = data.get('rut')
        codigo_verificador = data.get('codigo_verificador')
        if rut and codigo_verificador:
            rut_completo = str(rut) + str(codigo_verificador)
            if not validar_rut(rut_completo):
                return jsonify({"error": "RUT inválido"}), 400
        else:
            rut = None
            codigo_verificador = None

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se pudo obtener la sucursal activa"}), 400

        id_sucursal = usuario['id_sucursalactiva']

        # Validar que el contratista existe, está activo y pertenece a la sucursal del usuario
        cursor.execute("""
            SELECT c.id 
            FROM general_dim_contratista c
            INNER JOIN general_pivot_contratista_sucursal cs ON c.id = cs.id_contratista
            WHERE c.id = %s AND c.id_estado = 1 AND cs.id_sucursal = %s
        """, (data['id_contratista'], id_sucursal))
        if not cursor.fetchone():
            return jsonify({"error": "Contratista no encontrado, inactivo o no pertenece a su sucursal"}), 400

        # Validar que el porcentaje existe
        cursor.execute("SELECT id FROM general_dim_porcentajecontratista WHERE id = %s", (data['id_porcentaje'],))
        if not cursor.fetchone():
            return jsonify({"error": "Porcentaje no encontrado"}), 400

        # Validar que el estado existe
        cursor.execute("SELECT id FROM general_dim_estado WHERE id = %s", (data['id_estado'],))
        if not cursor.fetchone():
            return jsonify({"error": "Estado no encontrado"}), 400

        # Crear trabajador
        trabajador_id = str(uuid.uuid4())
        sql = """
            INSERT INTO general_dim_trabajador (
                id, rut, codigo_verificador, nombre, apellido_paterno, apellido_materno,
                id_contratista, id_porcentaje, id_estado, id_sucursal_activa
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            trabajador_id,
            rut,
            codigo_verificador,
            data['nombre'],
            data['apellido_paterno'],
            data.get('apellido_materno'),  # Opcional
            data['id_contratista'],
            data['id_porcentaje'],
            data['id_estado'],
            id_sucursal
        ))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Trabajador creado correctamente", "id": trabajador_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 📌 Editar trabajador (VERSIÓN FLEXIBLE)
@trabajadores_bp.route('/<string:trabajador_id>', methods=['PUT'])
@jwt_required()
def editar_trabajador(trabajador_id):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener trabajador actual
        cursor.execute("SELECT * FROM general_dim_trabajador WHERE id = %s", (trabajador_id,))
        trabajador_actual = cursor.fetchone()

        if not trabajador_actual:
            return jsonify({"error": "Trabajador no encontrado"}), 404

        # Validar RUT si se está modificando
        if 'rut' in data or 'codigo_verificador' in data:
            rut = data.get('rut', trabajador_actual['rut'])
            codigo_verificador = data.get('codigo_verificador', trabajador_actual['codigo_verificador'])
            if not validar_rut(str(rut) + codigo_verificador):
                return jsonify({"error": "RUT inválido"}), 400

        # Conservar valores existentes si no se mandan en el request
        rut = data.get('rut', trabajador_actual['rut'])
        codigo_verificador = data.get('codigo_verificador', trabajador_actual['codigo_verificador'])
        nombre = data.get('nombre', trabajador_actual['nombre'])
        apellido_paterno = data.get('apellido_paterno', trabajador_actual['apellido_paterno'])
        apellido_materno = data.get('apellido_materno', trabajador_actual['apellido_materno'])
        id_contratista = data.get('id_contratista', trabajador_actual['id_contratista'])
        id_porcentaje = data.get('id_porcentaje', trabajador_actual['id_porcentaje'])
        id_estado = data.get('id_estado', trabajador_actual['id_estado'])
        id_sucursal_activa = trabajador_actual['id_sucursal_activa']  # No se puede cambiar

        # Actualizar trabajador
        sql = """
            UPDATE general_dim_trabajador
            SET rut = %s, codigo_verificador = %s, nombre = %s,
                apellido_paterno = %s, apellido_materno = %s,
                id_contratista = %s, id_porcentaje = %s, id_estado = %s
            WHERE id = %s
        """
        cursor.execute(sql, (
            rut, codigo_verificador, nombre,
            apellido_paterno, apellido_materno,
            id_contratista, id_porcentaje, id_estado,
            trabajador_id
        ))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Trabajador actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener un trabajador por su ID
@trabajadores_bp.route('/<string:trabajador_id>', methods=['GET'])
@jwt_required()
def obtener_trabajador_por_id(trabajador_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT t.*, c.nombre as nombre_contratista, p.porcentaje, s.nombre as nombre_sucursal
            FROM general_dim_trabajador t
            LEFT JOIN general_dim_contratista c ON t.id_contratista = c.id
            LEFT JOIN general_dim_porcentajecontratista p ON t.id_porcentaje = p.id
            LEFT JOIN general_dim_sucursal s ON t.id_sucursal_activa = s.id
            WHERE t.id = %s
        """, (trabajador_id,))
        trabajador = cursor.fetchone()
        cursor.close()
        conn.close()
        if not trabajador:
            return jsonify({"error": "Trabajador no encontrado"}), 404
        return jsonify(trabajador), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener opciones para crear trabajador
@trabajadores_bp.route('/opciones-crear', methods=['GET'])
@jwt_required()
def obtener_opciones_crear_trabajador():
    try:
        usuario_id = get_jwt_identity()
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se pudo obtener la sucursal activa"}), 400
        
        id_sucursal = usuario['id_sucursalactiva']
        
        # Obtener contratistas disponibles (solo de la sucursal del usuario)
        cursor.execute("""
            SELECT c.id, c.nombre, c.rut, c.codigo_verificador
            FROM general_dim_contratista c
            INNER JOIN general_pivot_contratista_sucursal cs ON c.id = cs.id_contratista
            WHERE c.id_estado = 1 AND cs.id_sucursal = %s
            ORDER BY c.nombre ASC
        """, (id_sucursal,))
        contratistas = cursor.fetchall()
        
        # Obtener porcentajes disponibles
        cursor.execute("""
            SELECT id, porcentaje
            FROM general_dim_porcentajecontratista
            ORDER BY porcentaje ASC
        """)
        porcentajes = cursor.fetchall()
        
        # Obtener estados disponibles
        cursor.execute("""
            SELECT id, nombre
            FROM general_dim_estado
            ORDER BY nombre ASC
        """)
        estados = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "contratistas": contratistas,
            "porcentajes": porcentajes,
            "estados": estados,
            "sucursal_activa": id_sucursal
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener opciones para editar trabajador
@trabajadores_bp.route('/opciones-editar/<string:trabajador_id>', methods=['GET'])
@jwt_required()
def obtener_opciones_editar_trabajador(trabajador_id):
    try:
        usuario_id = get_jwt_identity()
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se pudo obtener la sucursal activa"}), 400
        
        id_sucursal = usuario['id_sucursalactiva']
        
        # Obtener trabajador actual
        cursor.execute("""
            SELECT t.*, c.nombre as nombre_contratista, p.porcentaje, s.nombre as nombre_sucursal
            FROM general_dim_trabajador t
            LEFT JOIN general_dim_contratista c ON t.id_contratista = c.id
            LEFT JOIN general_dim_porcentajecontratista p ON t.id_porcentaje = p.id
            LEFT JOIN general_dim_sucursal s ON t.id_sucursal_activa = s.id
            WHERE t.id = %s AND t.id_sucursal_activa = %s
        """, (trabajador_id, id_sucursal))
        
        trabajador = cursor.fetchone()
        if not trabajador:
            return jsonify({"error": "Trabajador no encontrado"}), 404
        
        # Obtener contratistas disponibles (solo de la sucursal del usuario)
        cursor.execute("""
            SELECT c.id, c.nombre, c.rut, c.codigo_verificador
            FROM general_dim_contratista c
            INNER JOIN general_pivot_contratista_sucursal cs ON c.id = cs.id_contratista
            WHERE c.id_estado = 1 AND cs.id_sucursal = %s
            ORDER BY c.nombre ASC
        """, (id_sucursal,))
        contratistas = cursor.fetchall()
        
        # Obtener porcentajes disponibles
        cursor.execute("""
            SELECT id, porcentaje
            FROM general_dim_porcentajecontratista
            ORDER BY porcentaje ASC
        """)
        porcentajes = cursor.fetchall()
        
        # Obtener estados disponibles
        cursor.execute("""
            SELECT id, nombre
            FROM general_dim_estado
            ORDER BY nombre ASC
        """)
        estados = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "trabajador": trabajador,
            "contratistas": contratistas,
            "porcentajes": porcentajes,
            "estados": estados,
            "sucursal_activa": id_sucursal
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Eliminar trabajador
@trabajadores_bp.route('/<string:trabajador_id>', methods=['DELETE'])
@jwt_required()
def eliminar_trabajador(trabajador_id):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se pudo obtener la sucursal activa"}), 400
        
        id_sucursal = usuario['id_sucursalactiva']
        
        # Verificar que el trabajador existe y pertenece a la sucursal del usuario
        cursor.execute("""
            SELECT id FROM general_dim_trabajador 
            WHERE id = %s AND id_sucursal_activa = %s
        """, (trabajador_id, id_sucursal))
        
        trabajador = cursor.fetchone()
        if not trabajador:
            return jsonify({"error": "Trabajador no encontrado o no tienes permisos para eliminarlo"}), 404
        
        # Eliminar el trabajador
        cursor.execute("DELETE FROM general_dim_trabajador WHERE id = %s", (trabajador_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Trabajador eliminado correctamente"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
