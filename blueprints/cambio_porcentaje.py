from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
from datetime import date, datetime
from flask_cors import cross_origin


cambio_porcentaje_bp = Blueprint('cambio_porcentaje_bp', __name__)


# 🚀 Endpoint para obtener rendimientos de contratista con estado de actividad 1 o 2
@cambio_porcentaje_bp.route('/', methods=['GET'])
@cross_origin()
@jwt_required()
def obtener_rendimientos_porcentaje():
    """
    Obtiene los rendimientos de contratista donde el estado de la actividad es 1 (CREADA) o 2 (REVISADA).
    Filtra por la sucursal activa del usuario autenticado.
    Retorna: fecha, labor, unidad de la actividad; trabajador, id_porcentaje_individual y rendimiento del rendimiento.
    """
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener la sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or usuario['id_sucursalactiva'] is None:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400

        id_sucursal = usuario['id_sucursalactiva']

        sql = """
            SELECT 
                rc.id,
                rc.id_actividad,
                rc.id_trabajador,
                rc.rendimiento,
                rc.id_porcentaje_individual,
                a.fecha,
                l.nombre AS labor,
                u.nombre AS unidad,
                CONCAT(
                    t.nombre, ' ', 
                    t.apellido_paterno, 
                    CASE 
                        WHEN t.apellido_materno IS NOT NULL THEN CONCAT(' ', t.apellido_materno) 
                        ELSE '' 
                    END
                ) AS trabajador,
                p.porcentaje AS porcentaje_actual
            FROM tarja_fact_rendimientocontratista rc
            INNER JOIN tarja_fact_actividad a ON rc.id_actividad = a.id
            INNER JOIN general_dim_labor l ON a.id_labor = l.id
            INNER JOIN tarja_dim_unidad u ON a.id_unidad = u.id
            INNER JOIN general_dim_trabajador t ON rc.id_trabajador = t.id
            LEFT JOIN general_dim_porcentajecontratista p ON rc.id_porcentaje_individual = p.id
            WHERE a.id_estadoactividad IN (1, 2)
            AND a.id_sucursalactiva = %s
            ORDER BY a.fecha DESC, l.nombre ASC, t.nombre ASC, t.apellido_paterno ASC
        """

        cursor.execute(sql, (id_sucursal,))
        rendimientos = cursor.fetchall()

        # Formatear fechas
        for rendimiento in rendimientos:
            if 'fecha' in rendimiento and isinstance(rendimiento['fecha'], (date, datetime)):
                rendimiento['fecha'] = rendimiento['fecha'].strftime('%Y-%m-%d')

        cursor.close()
        conn.close()

        return jsonify(rendimientos), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🚀 Endpoint para editar el porcentaje de un rendimiento
@cambio_porcentaje_bp.route('/<string:rendimiento_id>', methods=['PUT'])
@cross_origin()
@jwt_required()
def editar_porcentaje_rendimiento(rendimiento_id):
    """
    Edita solo el id_porcentaje_individual de un rendimiento de contratista.
    Solo permite editar si el estado de la actividad es 1 (CREADA) o 2 (REVISADA).
    Verifica que el rendimiento pertenezca a una actividad de la sucursal del usuario.
    """
    try:
        usuario_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'id_porcentaje_individual' not in data:
            return jsonify({"error": "Se requiere el campo id_porcentaje_individual"}), 400

        id_porcentaje_individual = data['id_porcentaje_individual']

        # Validar que id_porcentaje_individual sea un entero
        try:
            id_porcentaje_individual = int(id_porcentaje_individual)
        except (ValueError, TypeError):
            return jsonify({"error": "id_porcentaje_individual debe ser un número entero"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener la sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or usuario['id_sucursalactiva'] is None:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400

        id_sucursal = usuario['id_sucursalactiva']

        # Verificar que el rendimiento existe, obtener el estado de la actividad y verificar la sucursal
        cursor.execute("""
            SELECT rc.id, a.id_estadoactividad, a.id_sucursalactiva
            FROM tarja_fact_rendimientocontratista rc
            INNER JOIN tarja_fact_actividad a ON rc.id_actividad = a.id
            WHERE rc.id = %s
        """, (rendimiento_id,))
        
        rendimiento = cursor.fetchone()
        
        if not rendimiento:
            cursor.close()
            conn.close()
            return jsonify({"error": "Rendimiento no encontrado"}), 404

        # Verificar que el rendimiento pertenezca a la sucursal del usuario
        if rendimiento['id_sucursalactiva'] != id_sucursal:
            cursor.close()
            conn.close()
            return jsonify({
                "error": "No tienes permiso para editar este rendimiento. No pertenece a tu sucursal."
            }), 403

        # Verificar que el estado de la actividad permita edición (1 o 2)
        if rendimiento['id_estadoactividad'] not in (1, 2):
            cursor.close()
            conn.close()
            return jsonify({
                "error": "No se puede editar el porcentaje. La actividad debe estar en estado CREADA (1) o REVISADA (2)"
            }), 400

        # Verificar que el porcentaje existe
        cursor.execute("""
            SELECT id FROM general_dim_porcentajecontratista 
            WHERE id = %s
        """, (id_porcentaje_individual,))
        
        porcentaje = cursor.fetchone()
        
        if not porcentaje:
            cursor.close()
            conn.close()
            return jsonify({"error": "Porcentaje no encontrado"}), 400

        # Actualizar el porcentaje
        cursor.execute("""
            UPDATE tarja_fact_rendimientocontratista
            SET id_porcentaje_individual = %s
            WHERE id = %s
        """, (id_porcentaje_individual, rendimiento_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "message": "Porcentaje actualizado correctamente",
            "id": rendimiento_id,
            "id_porcentaje_individual": id_porcentaje_individual
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

