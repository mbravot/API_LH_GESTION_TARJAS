from flask import Blueprint, jsonify, request
from utils.db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
import uuid
from utils.validar_rut import validar_rut

contratistas_bp = Blueprint('contratistas_bp', __name__)

# Obtener contratistas
@contratistas_bp.route('', methods=['GET'])
@jwt_required()
def obtener_contratistas():
    try:
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

        # Obtener contratistas de la sucursal con cantidad de trabajadores activos
        cursor.execute("""
            SELECT c.*, 
                   COALESCE(COUNT(t.id), 0) as cantidad_trabajadores_activos
            FROM general_dim_contratista c
            JOIN general_pivot_contratista_sucursal p ON c.id = p.id_contratista
            LEFT JOIN general_dim_trabajador t ON c.id = t.id_contratista 
                AND t.id_sucursal_activa = %s 
                AND t.id_estado = 1  -- 1: activo
            WHERE p.id_sucursal = %s
            GROUP BY c.id, c.rut, c.codigo_verificador, c.nombre, c.id_estado
            ORDER BY c.nombre ASC
        """, (id_sucursal, id_sucursal))
        
        contratistas = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(contratistas), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Crear contratista
@contratistas_bp.route('/', methods=['POST'])
@jwt_required()
def crear_contratista():
    try:
        data = request.json
        usuario_id = get_jwt_identity()

        # Validar RUT
        rut_completo = str(data['rut']) + data['codigo_verificador']
        if not validar_rut(rut_completo):
            return jsonify({"error": "RUT inválido"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener la sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or not usuario['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400

        id_sucursal = usuario['id_sucursalactiva']

        # Crear contratista
        contratista_id = str(uuid.uuid4())
        sql = """
            INSERT INTO general_dim_contratista
            (id, rut, codigo_verificador, nombre, id_estado)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            contratista_id,
            data['rut'],
            data['codigo_verificador'],
            data['nombre'],
            data['id_estado']
        ))

        # Asociar contratista con la sucursal
        sql_pivot = """
            INSERT INTO general_pivot_contratista_sucursal (id_contratista, id_sucursal)
            VALUES (%s, %s)
        """
        cursor.execute(sql_pivot, (contratista_id, id_sucursal))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Contratista creado correctamente", "id": contratista_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar contratista
@contratistas_bp.route('/<string:contratista_id>', methods=['PUT'])
@jwt_required()
def editar_contratista(contratista_id):
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

        # Verificar que el contratista existe y pertenece a la sucursal del usuario
        cursor.execute("""
            SELECT c.* FROM general_dim_contratista c
            JOIN general_pivot_contratista_sucursal p ON c.id = p.id_contratista
            WHERE c.id = %s AND p.id_sucursal = %s
        """, (contratista_id, id_sucursal))
        
        contratista_actual = cursor.fetchone()
        if not contratista_actual:
            return jsonify({"error": "Contratista no encontrado o no tienes permisos para editarlo"}), 404

        # Validar RUT si se está modificando
        if 'rut' in data or 'codigo_verificador' in data:
            rut = data.get('rut', contratista_actual['rut'])
            codigo_verificador = data.get('codigo_verificador', contratista_actual['codigo_verificador'])
            if not validar_rut(str(rut) + codigo_verificador):
                return jsonify({"error": "RUT inválido"}), 400

        # Conservar valores existentes si no se mandan en el request
        rut = data.get('rut', contratista_actual['rut'])
        codigo_verificador = data.get('codigo_verificador', contratista_actual['codigo_verificador'])
        nombre = data.get('nombre', contratista_actual['nombre'])
        id_estado = data.get('id_estado', contratista_actual['id_estado'])

        # Actualizar contratista
        sql = """
            UPDATE general_dim_contratista
            SET rut = %s, codigo_verificador = %s, nombre = %s, id_estado = %s
            WHERE id = %s
        """
        cursor.execute(sql, (
            rut,
            codigo_verificador,
            nombre,
            id_estado,
            contratista_id
        ))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Contratista actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener un contratista por su ID
@contratistas_bp.route('/<string:contratista_id>', methods=['GET'])
@jwt_required()
def obtener_contratista_por_id(contratista_id):
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
        
        # Obtener contratista específico de la sucursal del usuario
        cursor.execute("""
            SELECT c.*, p.id_sucursal
            FROM general_dim_contratista c
            JOIN general_pivot_contratista_sucursal p ON c.id = p.id_contratista
            WHERE c.id = %s AND p.id_sucursal = %s
        """, (contratista_id, id_sucursal))
        contratista = cursor.fetchone()
        cursor.close()
        conn.close()
        if not contratista:
            return jsonify({"error": "Contratista no encontrado"}), 404
        return jsonify(contratista), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Eliminar contratista
@contratistas_bp.route('/<string:contratista_id>', methods=['DELETE'])
@jwt_required()
def eliminar_contratista(contratista_id):
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
        
        # Verificar que el contratista existe y pertenece a la sucursal del usuario
        cursor.execute("""
            SELECT c.id FROM general_dim_contratista c
            JOIN general_pivot_contratista_sucursal p ON c.id = p.id_contratista
            WHERE c.id = %s AND p.id_sucursal = %s
        """, (contratista_id, id_sucursal))
        
        if not cursor.fetchone():
            return jsonify({"error": "Contratista no encontrado o no tienes permisos para eliminarlo"}), 404
        
        # Eliminar la relación con la sucursal
        cursor.execute("""
            DELETE FROM general_pivot_contratista_sucursal 
            WHERE id_contratista = %s AND id_sucursal = %s
        """, (contratista_id, id_sucursal))
        
        # Verificar si el contratista tiene otras relaciones con sucursales
        cursor.execute("""
            SELECT COUNT(*) as count FROM general_pivot_contratista_sucursal 
            WHERE id_contratista = %s
        """, (contratista_id,))
        
        result = cursor.fetchone()
        if result['count'] == 0:
            # Si no tiene más relaciones, eliminar el contratista
            cursor.execute("DELETE FROM general_dim_contratista WHERE id = %s", (contratista_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Contratista eliminado correctamente"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener opciones para crear/editar contratistas
@contratistas_bp.route('/opciones', methods=['GET'])
@jwt_required()
def obtener_opciones_contratistas():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener estados
        cursor.execute("SELECT id, nombre FROM general_dim_estado ORDER BY nombre")
        estados = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'estados': estados
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
