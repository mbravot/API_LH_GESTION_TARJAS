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
                a.hora_inicio,
                a.hora_fin,
                a.tarifa,
                l.nombre AS labor, 
                co.nombre AS contratista, 
                tr.nombre AS tipo_rend,
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
            LEFT JOIN general_dim_contratista co ON a.id_contratista = co.id
            LEFT JOIN tarja_dim_tiporendimiento tr ON a.id_tiporendimiento = tr.id
            WHERE a.id_sucursalactiva = %s
            AND (a.id_estadoactividad = 1 OR a.id_estadoactividad = 2)  -- 1: creada, 2: revisada
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


