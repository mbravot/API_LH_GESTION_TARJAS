import datetime
from flask import Blueprint, jsonify, request
from utils.db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta


actividades_bp = Blueprint('actividades_bp', __name__)

# 🚀 Endpoint para obtener actividades por sucursal
@actividades_bp.route('/sucursal/<string:id_sucursal>', methods=['GET'])
@jwt_required()
def obtener_actividades_por_sucursal(id_sucursal):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT 
                a.id, 
                a.fecha, 
                a.id_estadoactividad,
                a.id_labor,
                a.id_unidad,
                a.id_tipotrabajador,
                a.id_tiporendimiento,
                a.id_contratista,
                a.id_sucursalactiva,
                a.id_tipoceco,
                a.id_usuario,
                a.hora_inicio,
                a.hora_fin,
                a.tarifa,
                l.nombre AS labor, 
                u.nombre AS nombre_unidad,
                co.nombre AS contratista, 
                tr.nombre AS tipo_rend,
                tc.nombre AS nombre_tipoceco,
                CASE 
                    WHEN usr.id_colaborador IS NOT NULL THEN 
                        CONCAT(col.nombre, ' ', col.apellido_paterno)
                    ELSE 
                        usr.usuario
                END AS nombre_usuario,
                CASE 
                    WHEN a.id_tipoceco = 1 THEN (SELECT ce.nombre FROM tarja_fact_cecoadministrativo ca JOIN general_dim_ceco ce ON ca.id_ceco = ce.id WHERE ca.id_actividad = a.id LIMIT 1)
                    WHEN a.id_tipoceco = 2 THEN (SELECT ce.nombre FROM tarja_fact_cecoproductivo cp JOIN general_dim_ceco ce ON cp.id_ceco = ce.id WHERE cp.id_actividad = a.id LIMIT 1)
                    WHEN a.id_tipoceco = 3 THEN (SELECT ce.nombre FROM tarja_fact_cecomaquinaria cm JOIN general_dim_ceco ce ON cm.id_ceco = ce.id WHERE cm.id_actividad = a.id LIMIT 1)
                    WHEN a.id_tipoceco = 4 THEN (SELECT ce.nombre FROM tarja_fact_cecoinversion ci JOIN general_dim_ceco ce ON ci.id_ceco = ce.id WHERE ci.id_actividad = a.id LIMIT 1)
                    WHEN a.id_tipoceco = 5 THEN (SELECT ce.nombre FROM tarja_fact_cecoriego cr JOIN general_dim_ceco ce ON cr.id_ceco = ce.id WHERE cr.id_actividad = a.id LIMIT 1)
                    ELSE NULL
                END AS nombre_ceco,
                EXISTS (
                    SELECT 1 
                    FROM tarja_fact_rendimientopropio rp 
                    WHERE rp.id_actividad = a.id
                    UNION
                    SELECT 1 
                    FROM tarja_fact_rendimientocontratista rc 
                    WHERE rc.id_actividad = a.id
                    UNION
                    SELECT 1 
                    FROM tarja_fact_redimientogrupal rg 
                    WHERE rg.id_actividad = a.id
                ) AS tiene_rendimiento
            FROM tarja_fact_actividad a
            LEFT JOIN general_dim_labor l ON a.id_labor = l.id
            LEFT JOIN tarja_dim_unidad u ON a.id_unidad = u.id
            LEFT JOIN general_dim_contratista co ON a.id_contratista = co.id
            LEFT JOIN tarja_dim_tiporendimiento tr ON a.id_tiporendimiento = tr.id
            LEFT JOIN general_dim_cecotipo tc ON a.id_tipoceco = tc.id
            LEFT JOIN general_dim_usuario usr ON a.id_usuario = usr.id
            LEFT JOIN general_dim_colaborador col ON usr.id_colaborador = col.id
            WHERE a.id_sucursalactiva = %s
            AND (a.id_estadoactividad = 1 OR a.id_estadoactividad = 2 OR a.id_estadoactividad = 3)  -- 1: creada, 2: revisada, 3: aprobada
            GROUP BY a.id
            ORDER BY a.fecha DESC
        """

        cursor.execute(sql, (id_sucursal,))
        actividades = cursor.fetchall()

        for actividad in actividades:
            if 'fecha' in actividad and isinstance(actividad['fecha'], (date, datetime)):
                actividad['fecha'] = actividad['fecha'].strftime('%Y-%m-%d')

            if isinstance(actividad['hora_inicio'], timedelta):
                actividad['hora_inicio'] = str(actividad['hora_inicio'])
            if isinstance(actividad['hora_fin'], timedelta):
                actividad['hora_fin'] = str(actividad['hora_fin'])

        cursor.close()
        conn.close()

        return jsonify(actividades), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🚀 Endpoint para editar una actividad existente
@actividades_bp.route('/<string:actividad_id>', methods=['PUT'])
@jwt_required()
def editar_actividad(actividad_id): 
    try:
        usuario_id = get_jwt_identity()
        data = request.json

        # Validar campos requeridos según la tabla (excepto fecha, ya la tenemos)
        campos_requeridos = [
            'fecha', 'id_tipotrabajador', 'id_tiporendimiento', 'id_labor',
            'id_unidad', 'id_tipoceco', 'tarifa', 'hora_inicio', 'hora_fin', 'id_estadoactividad'
        ]
        for campo in campos_requeridos:
            if campo not in data or data[campo] in [None, '']:
                return jsonify({"error": f"El campo {campo} es requerido"}), 400

        # Validar id_contratista solo si id_tipotrabajador es 2
        id_contratista = data.get('id_contratista')
        if int(data['id_tipotrabajador']) == 2:
            if not id_contratista:
                return jsonify({"error": "El campo id_contratista es requerido cuando id_tipotrabajador es 2"}), 400
        else:
            id_contratista = None

        fecha = data.get('fecha')
        id_labor = data.get('id_labor')
        id_unidad = data.get('id_unidad')
        id_tipotrabajador = data.get('id_tipotrabajador')
        id_tiporendimiento = data.get('id_tiporendimiento')
        hora_inicio = data.get('hora_inicio')
        hora_fin = data.get('hora_fin')
        id_estadoactividad = data.get('id_estadoactividad')
        tarifa = data.get('tarifa')
        id_tipoceco = data.get('id_tipoceco')

        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            UPDATE tarja_fact_actividad 
            SET fecha = %s,
                id_labor = %s,
                id_unidad = %s,
                id_tipotrabajador = %s,
                id_contratista = %s,
                id_tiporendimiento = %s,
                hora_inicio = %s,
                hora_fin = %s,
                id_estadoactividad = %s,
                tarifa = %s,
                id_tipoceco = %s
            WHERE id = %s AND id_usuario = %s
        """
        valores = (fecha, id_labor, id_unidad, id_tipotrabajador,
                  id_contratista, id_tiporendimiento, hora_inicio,
                  hora_fin, id_estadoactividad, tarifa, id_tipoceco, actividad_id, usuario_id)

        cursor.execute(sql, valores)
        conn.commit()

        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Actividad no encontrada o no tienes permiso para editarla"}), 404

        cursor.close()
        conn.close()

        return jsonify({"message": "Actividad actualizada correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para cambiar solo el estado de una actividad
@actividades_bp.route('/<string:actividad_id>/estado', methods=['PUT'])
@jwt_required()
def cambiar_estado_actividad(actividad_id):
    try:
        usuario_id = get_jwt_identity()
        data = request.json

        # Solo validar que se envíe el nuevo estado
        if 'id_estadoactividad' not in data:
            return jsonify({"error": "El campo id_estadoactividad es requerido"}), 400

        nuevo_estado = data.get('id_estadoactividad')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Solo actualizar el estado
        sql = """
            UPDATE tarja_fact_actividad 
            SET id_estadoactividad = %s
            WHERE id = %s AND id_usuario = %s
        """
        valores = (nuevo_estado, actividad_id, usuario_id)

        cursor.execute(sql, valores)
        conn.commit()

        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Actividad no encontrada o no tienes permiso para editarla"}), 404

        cursor.close()
        conn.close()

        return jsonify({"message": "Estado de actividad actualizado correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para eliminar una actividad existente
@actividades_bp.route('/<string:actividad_id>', methods=['DELETE'])
@jwt_required()
def eliminar_actividad(actividad_id):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor()
        # Solo permitir eliminar si la actividad es del usuario
        cursor.execute("DELETE FROM tarja_fact_actividad WHERE id = %s AND id_usuario = %s", (actividad_id, usuario_id))
        conn.commit()
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Actividad no encontrada o no tienes permiso para eliminarla"}), 404
        cursor.close()
        conn.close()
        return jsonify({"message": "Actividad eliminada correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


