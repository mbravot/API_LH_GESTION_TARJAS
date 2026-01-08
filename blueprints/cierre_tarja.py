from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
from datetime import date, datetime
from flask_cors import cross_origin

cierre_tarja_bp = Blueprint('cierre_tarja_bp', __name__)


# 🚀 Endpoint para obtener actividades con estado 3 (aprobada) o 4 (finalizada)
@cierre_tarja_bp.route('/', methods=['GET'])
@cross_origin()
@jwt_required()
def obtener_actividades_cierre():
    """
    Obtiene las actividades con id_estadoactividad 3 (aprobada) o 4 (finalizada).
    Filtra por la sucursal activa del usuario autenticado.
    Retorna: fecha, usuario, ceco, labor, unidad, contratista, tipo rendimiento, tarifa, estado, oc.
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
                a.id,
                a.fecha,
                CONCAT(
                    usr.nombre, ' ', 
                    usr.apellido_paterno, 
                    CASE 
                        WHEN usr.apellido_materno IS NOT NULL THEN CONCAT(' ', usr.apellido_materno) 
                        ELSE '' 
                    END
                ) AS usuario,
                CASE 
                    WHEN a.id_tipoceco = 1 THEN (SELECT ce.nombre FROM tarja_fact_cecoadministrativo ca JOIN general_dim_ceco ce ON ca.id_ceco = ce.id WHERE ca.id_actividad = a.id LIMIT 1)
                    WHEN a.id_tipoceco = 2 THEN (SELECT ce.nombre FROM tarja_fact_cecoproductivo cp JOIN general_dim_ceco ce ON cp.id_ceco = ce.id WHERE cp.id_actividad = a.id LIMIT 1)
                    WHEN a.id_tipoceco = 3 THEN (SELECT ce.nombre FROM tarja_fact_cecomaquinaria cm JOIN general_dim_ceco ce ON cm.id_ceco = ce.id WHERE cm.id_actividad = a.id LIMIT 1)
                    WHEN a.id_tipoceco = 4 THEN (SELECT ce.nombre FROM tarja_fact_cecoinversion ci JOIN general_dim_ceco ce ON ci.id_ceco = ce.id WHERE ci.id_actividad = a.id LIMIT 1)
                    WHEN a.id_tipoceco = 5 THEN (SELECT ce.nombre FROM tarja_fact_cecoriego cr JOIN general_dim_ceco ce ON cr.id_ceco = ce.id WHERE cr.id_actividad = a.id LIMIT 1)
                    ELSE NULL
                END AS ceco,
                l.nombre AS labor,
                u.nombre AS unidad,
                COALESCE(co.nombre, 'N/A') AS contratista,
                tr.nombre AS tipo_rendimiento,
                a.tarifa,
                ea.nombre AS estado,
                a.oc
            FROM tarja_fact_actividad a
            INNER JOIN general_dim_labor l ON a.id_labor = l.id
            INNER JOIN tarja_dim_unidad u ON a.id_unidad = u.id
            LEFT JOIN general_dim_contratista co ON a.id_contratista = co.id
            INNER JOIN tarja_dim_tiporendimiento tr ON a.id_tiporendimiento = tr.id
            INNER JOIN general_dim_usuario usr ON a.id_usuario = usr.id
            INNER JOIN tarja_dim_estadoactividad ea ON a.id_estadoactividad = ea.id
            WHERE a.id_estadoactividad IN (3, 4)
            AND a.id_sucursalactiva = %s
            ORDER BY a.fecha DESC, l.nombre ASC
        """

        cursor.execute(sql, (id_sucursal,))
        actividades = cursor.fetchall()

        # Formatear fechas
        for actividad in actividades:
            if 'fecha' in actividad and isinstance(actividad['fecha'], (date, datetime)):
                actividad['fecha'] = actividad['fecha'].strftime('%Y-%m-%d')

        cursor.close()
        conn.close()

        return jsonify(actividades), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🚀 Endpoint para editar el campo oc de una actividad
@cierre_tarja_bp.route('/<string:actividad_id>', methods=['PUT'])
@cross_origin()
@jwt_required()
def editar_oc_actividad(actividad_id):
    """
    Edita el campo oc (orden de compra) de una actividad.
    Solo permite editar si el estado de la actividad es 3 (aprobada) o 4 (finalizada).
    Verifica que la actividad pertenezca a la sucursal del usuario.
    """
    try:
        usuario_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'oc' not in data:
            return jsonify({"error": "Se requiere el campo oc"}), 400

        oc = data['oc']

        # Validar que oc sea un entero o None
        if oc is not None:
            try:
                oc = int(oc)
            except (ValueError, TypeError):
                return jsonify({"error": "oc debe ser un número entero o null"}), 400

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

        # Verificar que la actividad existe, obtener el estado y verificar la sucursal
        cursor.execute("""
            SELECT id, id_estadoactividad, id_sucursalactiva
            FROM tarja_fact_actividad
            WHERE id = %s
        """, (actividad_id,))
        
        actividad = cursor.fetchone()
        
        if not actividad:
            cursor.close()
            conn.close()
            return jsonify({"error": "Actividad no encontrada"}), 404

        # Verificar que la actividad pertenezca a la sucursal del usuario
        if actividad['id_sucursalactiva'] != id_sucursal:
            cursor.close()
            conn.close()
            return jsonify({
                "error": "No tienes permiso para editar esta actividad. No pertenece a tu sucursal."
            }), 403

        # Verificar que el estado de la actividad permita edición (3 o 4)
        if actividad['id_estadoactividad'] not in (3, 4):
            cursor.close()
            conn.close()
            return jsonify({
                "error": "No se puede editar el oc. La actividad debe estar en estado APROBADA (3) o FINALIZADA (4)"
            }), 400

        # Actualizar el campo oc
        cursor.execute("""
            UPDATE tarja_fact_actividad
            SET oc = %s
            WHERE id = %s
        """, (oc, actividad_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "message": "OC actualizado correctamente",
            "id": actividad_id,
            "oc": oc
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

