from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
import uuid

rendimientopropio_bp = Blueprint('rendimientopropio_bp', __name__)

# Listar rendimientos propios por actividad (filtrado por sucursal del usuario)
@rendimientopropio_bp.route('/actividad/<string:id_actividad>', methods=['GET'])
@jwt_required()
def listar_rendimientos_propios_por_actividad(id_actividad):
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
        # Verificar que la actividad pertenece a la sucursal y obtener fecha, labor y CECO principal
        cursor.execute("""
            SELECT 
                a.fecha, 
                l.nombre AS labor,
                a.id_estadoactividad,
                COALESCE(cp.id_ceco, ci.id_ceco, cm.id_ceco, cr.id_ceco, ca.id_ceco) AS id_ceco
            FROM tarja_fact_actividad a
            JOIN general_dim_labor l ON a.id_labor = l.id
            LEFT JOIN tarja_fact_cecoproductivo cp ON a.id = cp.id_actividad
            LEFT JOIN tarja_fact_cecoinversion ci ON a.id = ci.id_actividad
            LEFT JOIN tarja_fact_cecomaquinaria cm ON a.id = cm.id_actividad
            LEFT JOIN tarja_fact_cecoriego cr ON a.id = cr.id_actividad
            LEFT JOIN tarja_fact_cecoadministrativo ca ON a.id = ca.id_actividad
            WHERE a.id = %s AND a.id_sucursalactiva = %s
            LIMIT 1
        """, (id_actividad, id_sucursal))
        actividad = cursor.fetchone()
        if not actividad:
            return jsonify({"error": "Actividad no encontrada o no pertenece a tu sucursal"}), 404
        # Comentamos esta validación para permitir ver rendimientos en cualquier estado
        # if actividad['id_estadoactividad'] != 1:
        #     return jsonify({"rendimientos": []}), 200
        # Obtener nombre del CECO
        nombre_ceco = None
        if actividad['id_ceco']:
            cursor.execute("SELECT nombre FROM general_dim_ceco WHERE id = %s", (actividad['id_ceco'],))
            ceco = cursor.fetchone()
            if ceco:
                nombre_ceco = ceco['nombre']
        # Obtener rendimientos propios
        cursor.execute("""
            SELECT r.id, r.id_colaborador, c.nombre as nombre_colaborador, c.apellido_paterno, c.apellido_materno,
                   r.horas_trabajadas, r.rendimiento, r.horas_extras, r.id_bono
            FROM tarja_fact_rendimientopropio r
            JOIN general_dim_colaborador c ON r.id_colaborador = c.id
            WHERE r.id_actividad = %s
            ORDER BY c.nombre, c.apellido_paterno, c.apellido_materno
        """, (id_actividad,))
        rendimientos = cursor.fetchall()
        cursor.close()
        conn.close()
        # Formatear nombre completo del colaborador
        for r in rendimientos:
            r['nombre_colaborador'] = f"{r['nombre_colaborador']} {r['apellido_paterno']} {r['apellido_materno'] or ''}".strip()
            del r['apellido_paterno']
            del r['apellido_materno']
        return jsonify({
            "actividad": {
                "fecha": str(actividad['fecha']),
                "labor": actividad['labor'],
                "ceco": nombre_ceco,
                "estado": actividad['id_estadoactividad']
            },
            "rendimientos": rendimientos,
            "debug": {
                "id_actividad": id_actividad,
                "cantidad_rendimientos": len(rendimientos),
                "estado_actividad": actividad['id_estadoactividad'],
                "mensaje": "No hay rendimientos registrados para esta actividad" if not rendimientos else f"Se encontraron {len(rendimientos)} rendimientos"
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar horas trabajadas (y opcionalmente otros campos) de un rendimiento propio
@rendimientopropio_bp.route('/<string:id_rendimiento>', methods=['PUT'])
@jwt_required()
def editar_rendimiento_propio(id_rendimiento):
    try:
        if not id_rendimiento or id_rendimiento.lower() == 'null':
            return jsonify({"error": "ID de rendimiento inválido"}), 400
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Verificar que el rendimiento existe
        cursor.execute("SELECT * FROM tarja_fact_rendimientopropio WHERE id = %s", (id_rendimiento,))
        rendimiento = cursor.fetchone()
        if not rendimiento:
            return jsonify({"error": "Rendimiento no encontrado"}), 404
        # Actualizar campos editables
        sql = """
            UPDATE tarja_fact_rendimientopropio
            SET horas_trabajadas = %s, horas_extras = %s, rendimiento = %s, id_bono = %s
            WHERE id = %s
        """
        cursor.execute(sql, (
            data.get('horas_trabajadas', rendimiento['horas_trabajadas']),
            data.get('horas_extras', rendimiento['horas_extras']),
            data.get('rendimiento', rendimiento['rendimiento']),
            data.get('id_bono', rendimiento['id_bono']),
            id_rendimiento
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Listar actividades de la sucursal del usuario
@rendimientopropio_bp.route('/actividades', methods=['GET'])
@jwt_required()
def listar_actividades_sucursal_usuario():
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
        # Listar actividades de la sucursal con estado 1 (creada) y obtener el CECO principal
        cursor.execute("""
            SELECT a.id, a.fecha, l.nombre AS labor, a.id_estadoactividad, a.id_tipotrabajador,
                   COALESCE(cp.id_ceco, ci.id_ceco, cm.id_ceco, cr.id_ceco, ca.id_ceco) AS id_ceco
            FROM tarja_fact_actividad a
            JOIN general_dim_labor l ON a.id_labor = l.id
            LEFT JOIN tarja_fact_cecoproductivo cp ON a.id = cp.id_actividad
            LEFT JOIN tarja_fact_cecoinversion ci ON a.id = ci.id_actividad
            LEFT JOIN tarja_fact_cecomaquinaria cm ON a.id = cm.id_actividad
            LEFT JOIN tarja_fact_cecoriego cr ON a.id = cr.id_actividad
            LEFT JOIN tarja_fact_cecoadministrativo ca ON a.id = ca.id_actividad
            WHERE a.id_sucursalactiva = %s AND a.id_estadoactividad = 1 AND a.id_tipotrabajador = 1 AND a.id_usuario = %s
            ORDER BY a.fecha DESC
        """, (id_sucursal, usuario_id))
        actividades = cursor.fetchall()
        # Obtener nombre del CECO para cada actividad
        for act in actividades:
            nombre_ceco = None
            if act['id_ceco']:
                cursor.execute("SELECT nombre FROM general_dim_ceco WHERE id = %s", (act['id_ceco'],))
                ceco = cursor.fetchone()
                if ceco:
                    nombre_ceco = ceco['nombre']
            act['ceco'] = nombre_ceco
            del act['id_ceco']
        cursor.close()
        conn.close()
        return jsonify(actividades), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500 