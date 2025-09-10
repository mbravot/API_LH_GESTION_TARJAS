import datetime
from flask import Blueprint, jsonify, request
from utils.db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta
from flask_cors import cross_origin
import uuid


rendimientos_bp = Blueprint('rendimientos_bp', __name__)

# 🚀 Endpoint para obtener rendimientos según el tipo de la actividad
@rendimientos_bp.route('/<string:id_actividad>', methods=['GET'])
@cross_origin()
def obtener_rendimientos(id_actividad):
    if id_actividad is None or id_actividad.lower() == 'null' or id_actividad.strip() == '':
        return jsonify({"error": "El parámetro id_actividad es inválido o no fue proporcionado"}), 400
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_tiporendimiento, id_tipotrabajador FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
        actividad = cursor.fetchone()
        if not actividad:
            cursor.close()
            conn.close()
            return jsonify({"error": "Actividad no encontrada"}), 404
        tipo = actividad['id_tiporendimiento']
        tipo_trabajador = actividad['id_tipotrabajador']
        rendimientos = []
        if tipo == 1:  # Individual
            if tipo_trabajador == 1:  # Propio
                cursor.execute("""
                    SELECT r.*, l.nombre AS labor, c.nombre AS colaborador, b.nombre AS bono,
                           COALESCE(ce.nombre, 
                               CASE 
                                   WHEN a.id_tipoceco = 1 THEN (SELECT ce2.nombre FROM tarja_fact_cecoadministrativo ca2 JOIN general_dim_ceco ce2 ON ca2.id_ceco = ce2.id WHERE ca2.id_actividad = a.id LIMIT 1)
                                   WHEN a.id_tipoceco = 2 THEN (SELECT ce2.nombre FROM tarja_fact_cecoproductivo cp2 JOIN general_dim_ceco ce2 ON cp2.id_ceco = ce2.id WHERE cp2.id_actividad = a.id LIMIT 1)
                                   WHEN a.id_tipoceco = 3 THEN (SELECT ce2.nombre FROM tarja_fact_cecoinversion ci2 JOIN general_dim_ceco ce2 ON ci2.id_ceco = ce2.id WHERE ci2.id_actividad = a.id LIMIT 1)
                                   WHEN a.id_tipoceco = 4 THEN (SELECT ce2.nombre FROM tarja_fact_cecomaquinaria cm2 JOIN general_dim_ceco ce2 ON cm2.id_ceco = ce2.id WHERE cm2.id_actividad = a.id LIMIT 1)
                                   WHEN a.id_tipoceco = 5 THEN (SELECT ce2.nombre FROM tarja_fact_cecoriego cr2 JOIN general_dim_ceco ce2 ON cr2.id_ceco = ce2.id WHERE cr2.id_actividad = a.id LIMIT 1)
                               END
                           ) as nombre_ceco
                    FROM tarja_fact_rendimientopropio r
                    LEFT JOIN tarja_fact_actividad a ON r.id_actividad = a.id
                    LEFT JOIN general_dim_labor l ON a.id_labor = l.id
                    LEFT JOIN general_dim_colaborador c ON r.id_colaborador = c.id
                    LEFT JOIN general_dim_bono b ON r.id_bono = b.id
                    LEFT JOIN general_dim_ceco ce ON r.id_ceco = ce.id
                    WHERE r.id_actividad = %s
                """, (id_actividad,))
                rendimientos = cursor.fetchall()
            elif tipo_trabajador == 2:  # Contratista
                cursor.execute("""
                    SELECT r.*, l.nombre AS labor, t.nombre AS trabajador, p.porcentaje AS porcentaje_trabajador,
                           COALESCE(cp.id_ceco, ci.id_ceco, cm.id_ceco, cr.id_ceco, ca.id_ceco) AS id_ceco,
                           COALESCE(ce.nombre, 
                               CASE 
                                   WHEN a.id_tipoceco = 1 THEN (SELECT ce2.nombre FROM tarja_fact_cecoadministrativo ca2 JOIN general_dim_ceco ce2 ON ca2.id_ceco = ce2.id WHERE ca2.id_actividad = a.id LIMIT 1)
                                   WHEN a.id_tipoceco = 2 THEN (SELECT ce2.nombre FROM tarja_fact_cecoproductivo cp2 JOIN general_dim_ceco ce2 ON cp2.id_ceco = ce2.id WHERE cp2.id_actividad = a.id LIMIT 1)
                                   WHEN a.id_tipoceco = 3 THEN (SELECT ce2.nombre FROM tarja_fact_cecoinversion ci2 JOIN general_dim_ceco ce2 ON ci2.id_ceco = ce2.id WHERE ci2.id_actividad = a.id LIMIT 1)
                                   WHEN a.id_tipoceco = 4 THEN (SELECT ce2.nombre FROM tarja_fact_cecomaquinaria cm2 JOIN general_dim_ceco ce2 ON cm2.id_ceco = ce2.id WHERE cm2.id_actividad = a.id LIMIT 1)
                                   WHEN a.id_tipoceco = 5 THEN (SELECT ce2.nombre FROM tarja_fact_cecoriego cr2 JOIN general_dim_ceco ce2 ON cr2.id_ceco = ce2.id WHERE cr2.id_actividad = a.id LIMIT 1)
                               END
                           ) as nombre_ceco
                    FROM tarja_fact_rendimientocontratista r
                    LEFT JOIN tarja_fact_actividad a ON r.id_actividad = a.id
                    LEFT JOIN general_dim_labor l ON a.id_labor = l.id
                    LEFT JOIN general_dim_trabajador t ON r.id_trabajador = t.id
                    LEFT JOIN general_dim_porcentajecontratista p ON r.id_porcentaje_individual = p.id
                    LEFT JOIN tarja_fact_cecoproductivo cp ON a.id = cp.id_actividad
                    LEFT JOIN tarja_fact_cecoinversion ci ON a.id = ci.id_actividad
                    LEFT JOIN tarja_fact_cecomaquinaria cm ON a.id = cm.id_actividad
                    LEFT JOIN tarja_fact_cecoriego cr ON a.id = cr.id_actividad
                    LEFT JOIN tarja_fact_cecoadministrativo ca ON a.id = ca.id_actividad
                    LEFT JOIN general_dim_ceco ce ON COALESCE(cp.id_ceco, ci.id_ceco, cm.id_ceco, cr.id_ceco, ca.id_ceco) = ce.id
                    WHERE r.id_actividad = %s
                """, (id_actividad,))
                rendimientos = cursor.fetchall()
        elif tipo == 2:  # Grupal
            cursor.execute("""
                SELECT rg.*, a.id_labor, l.nombre AS labor, p.porcentaje AS porcentaje_grupal,
                       COALESCE(cp.id_ceco, ci.id_ceco, cm.id_ceco, cr.id_ceco, ca.id_ceco) AS id_ceco,
                       COALESCE(ce.nombre, 
                           CASE 
                               WHEN a.id_tipoceco = 1 THEN (SELECT ce2.nombre FROM tarja_fact_cecoadministrativo ca2 JOIN general_dim_ceco ce2 ON ca2.id_ceco = ce2.id WHERE ca2.id_actividad = a.id LIMIT 1)
                               WHEN a.id_tipoceco = 2 THEN (SELECT ce2.nombre FROM tarja_fact_cecoproductivo cp2 JOIN general_dim_ceco ce2 ON cp2.id_ceco = ce2.id WHERE cp2.id_actividad = a.id LIMIT 1)
                               WHEN a.id_tipoceco = 3 THEN (SELECT ce2.nombre FROM tarja_fact_cecoinversion ci2 JOIN general_dim_ceco ce2 ON ci2.id_ceco = ce2.id WHERE ci2.id_actividad = a.id LIMIT 1)
                               WHEN a.id_tipoceco = 4 THEN (SELECT ce2.nombre FROM tarja_fact_cecomaquinaria cm2 JOIN general_dim_ceco ce2 ON cm2.id_ceco = ce2.id WHERE cm2.id_actividad = a.id LIMIT 1)
                               WHEN a.id_tipoceco = 5 THEN (SELECT ce2.nombre FROM tarja_fact_cecoriego cr2 JOIN general_dim_ceco ce2 ON cr2.id_ceco = ce2.id WHERE cr2.id_actividad = a.id LIMIT 1)
                           END
                       ) as nombre_ceco
                FROM tarja_fact_redimientogrupal rg
                LEFT JOIN tarja_fact_actividad a ON rg.id_actividad = a.id
                LEFT JOIN general_dim_labor l ON a.id_labor = l.id
                LEFT JOIN general_dim_porcentajecontratista p ON rg.id_porcentaje = p.id
                LEFT JOIN tarja_fact_cecoproductivo cp ON a.id = cp.id_actividad
                LEFT JOIN tarja_fact_cecoinversion ci ON a.id = ci.id_actividad
                LEFT JOIN tarja_fact_cecomaquinaria cm ON a.id = cm.id_actividad
                LEFT JOIN tarja_fact_cecoriego cr ON a.id = cr.id_actividad
                LEFT JOIN tarja_fact_cecoadministrativo ca ON a.id = ca.id_actividad
                LEFT JOIN general_dim_ceco ce ON COALESCE(cp.id_ceco, ci.id_ceco, cm.id_ceco, cr.id_ceco, ca.id_ceco) = ce.id
                WHERE rg.id_actividad = %s
            """, (id_actividad,))
            rendimientos = cursor.fetchall()
        cursor.close()
        conn.close()
        if not rendimientos:
            return jsonify({
                "rendimientos": [],
                "debug": {
                    "id_actividad": id_actividad,
                    "tipo_rendimiento": tipo,
                    "tipo_trabajador": tipo_trabajador,
                    "mensaje": "No se encontraron rendimientos para esta actividad"
                }
            }), 200
        return jsonify({
            "rendimientos": rendimientos,
            "debug": {
                "id_actividad": id_actividad,
                "tipo_rendimiento": tipo,
                "tipo_trabajador": tipo_trabajador,
                "cantidad_rendimientos": len(rendimientos)
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🚀 Endpoint para editar un rendimiento existente según el tipo de la actividad
@rendimientos_bp.route('/<string:rendimiento_id>', methods=['PUT'])
@jwt_required()
def editar_rendimiento(rendimiento_id):
    try:
        data = request.json
        id_actividad = data.get('id_actividad')
        if not id_actividad:
            return jsonify({"error": "Falta id_actividad"}), 400
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Consultar el tipo de rendimiento de la actividad
        cursor.execute("SELECT id_tiporendimiento FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
        actividad = cursor.fetchone()
        if not actividad:
            cursor.close()
            conn.close()
            return jsonify({"error": "Actividad no encontrada"}), 404
        tipo = actividad['id_tiporendimiento']
        if tipo == 1:  # Individual
            sql = """
                UPDATE tarja_fact_rendimientopropio 
                SET id_trabajador = %s,
                    id_colaborador = %s,
                    rendimiento = %s,
                    horas_trabajadas = %s,
                    horas_extras = %s,
                    id_bono = %s,
                    id_porcentaje_individual = %s
                WHERE id = %s
            """
            # Consultar el tipo de trabajador de la actividad
            cursor.execute("SELECT id_tipotrabajador FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
            actividad_tipo = cursor.fetchone()
            if not actividad_tipo:
                cursor.close()
                conn.close()
                return jsonify({"error": "No se pudo determinar el tipo de trabajador de la actividad"}), 400
            tipo_trabajador = actividad_tipo['id_tipotrabajador']
            # Validación según tipo de trabajador
            if tipo_trabajador == 1:
                # Propio: solo id_colaborador, id_trabajador debe ser None
                if not data.get('id_colaborador'):
                    return jsonify({"error": "Falta id_colaborador para trabajador propio"}), 400
                valores = (
                    None,  # id_trabajador
                    data.get('id_colaborador'),
                    data.get('rendimiento'),
                    data.get('horas_trabajadas'),
                    data.get('horas_extras'),
                    data.get('id_bono'),
                    data.get('id_porcentaje_individual'),
                    rendimiento_id
                )
            elif tipo_trabajador == 2:
                # Contratista: solo id_trabajador, id_colaborador debe ser None
                if not data.get('id_trabajador'):
                    return jsonify({"error": "Falta id_trabajador para trabajador contratista"}), 400
                valores = (
                    data.get('id_trabajador'),
                    None,  # id_colaborador
                    data.get('rendimiento'),
                    data.get('horas_trabajadas'),
                    data.get('horas_extras'),
                    data.get('id_bono'),
                    data.get('id_porcentaje_individual'),
                    rendimiento_id
                )
            else:
                return jsonify({"error": "Tipo de trabajador no soportado"}), 400
            cursor.execute(sql, valores)
        elif tipo == 2:  # Grupal
            sql = """
                UPDATE tarja_fact_redimientogrupal 
                SET rendimiento_total = %s,
                    cantidad_trab = %s,
                    id_porcentaje = %s
                WHERE id = %s
            """
            valores = (
                data.get('rendimiento_total'),
                data.get('cantidad_trab'),
                data.get('id_porcentaje'),
                rendimiento_id
            )
            cursor.execute(sql, valores)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para eliminar un rendimiento individual
@rendimientos_bp.route('/individual/<string:rendimiento_id>', methods=['DELETE'])
@jwt_required()
def eliminar_rendimiento_individual(rendimiento_id):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que el rendimiento exista y pertenezca a una actividad del usuario
        cursor.execute("""
            SELECT r.id 
            FROM tarja_fact_rendimientopropio r
            JOIN tarja_fact_actividad a ON r.id_actividad = a.id
            WHERE r.id = %s AND a.id_usuario = %s
        """, (rendimiento_id, usuario_id))
        
        rendimiento = cursor.fetchone()
        if not rendimiento:
            cursor.close()
            conn.close()
            return jsonify({"error": "Rendimiento no encontrado o no tienes permiso para eliminarlo"}), 404
        
        # Eliminar el rendimiento
        cursor.execute("DELETE FROM tarja_fact_rendimientopropio WHERE id = %s", (rendimiento_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento individual eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para eliminar un rendimiento grupal
@rendimientos_bp.route('/grupal/<string:rendimiento_id>', methods=['DELETE'])
@jwt_required()
def eliminar_rendimiento_grupal(rendimiento_id):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verificar que el rendimiento exista y pertenezca a una actividad del usuario
        cursor.execute("""
            SELECT rg.id 
            FROM tarja_fact_redimientogrupal rg
            JOIN tarja_fact_actividad a ON rg.id_actividad = a.id
            WHERE rg.id = %s AND a.id_usuario = %s
        """, (rendimiento_id, usuario_id))
        
        rendimiento = cursor.fetchone()
        if not rendimiento:
            cursor.close()
            conn.close()
            return jsonify({"error": "Rendimiento grupal no encontrado o no tienes permiso para eliminarlo"}), 404
        
        # Eliminar el rendimiento
        cursor.execute("DELETE FROM tarja_fact_redimientogrupal WHERE id = %s", (rendimiento_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento grupal eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Obtener rendimientos individuales propios
@rendimientos_bp.route('/individual/propio', methods=['GET'])
@jwt_required()
def obtener_rendimientos_individuales_propios():
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
        id_actividad = request.args.get('id_actividad')

        sql = """
            SELECT 
                r.id,
                r.id_actividad,
                r.id_colaborador,
                r.rendimiento,
                r.horas_trabajadas,
                r.horas_extras,
                r.id_bono,
                r.id_ceco,
                l.nombre as nombre_actividad,
                c.nombre as nombre_colaborador,
                b.nombre as nombre_bono,
                COALESCE(ce.nombre, 
                    CASE 
                        WHEN a.id_tipoceco = 1 THEN (SELECT ce2.nombre FROM tarja_fact_cecoadministrativo ca2 JOIN general_dim_ceco ce2 ON ca2.id_ceco = ce2.id WHERE ca2.id_actividad = a.id LIMIT 1)
                        WHEN a.id_tipoceco = 2 THEN (SELECT ce2.nombre FROM tarja_fact_cecoproductivo cp2 JOIN general_dim_ceco ce2 ON cp2.id_ceco = ce2.id WHERE cp2.id_actividad = a.id LIMIT 1)
                        WHEN a.id_tipoceco = 3 THEN (SELECT ce2.nombre FROM tarja_fact_cecoinversion ci2 JOIN general_dim_ceco ce2 ON ci2.id_ceco = ce2.id WHERE ci2.id_actividad = a.id LIMIT 1)
                        WHEN a.id_tipoceco = 4 THEN (SELECT ce2.nombre FROM tarja_fact_cecomaquinaria cm2 JOIN general_dim_ceco ce2 ON cm2.id_ceco = ce2.id WHERE cm2.id_actividad = a.id LIMIT 1)
                        WHEN a.id_tipoceco = 5 THEN (SELECT ce2.nombre FROM tarja_fact_cecoriego cr2 JOIN general_dim_ceco ce2 ON cr2.id_ceco = ce2.id WHERE cr2.id_actividad = a.id LIMIT 1)
                    END
                ) as nombre_ceco
            FROM tarja_fact_rendimientopropio r
            JOIN tarja_fact_actividad a ON r.id_actividad = a.id
            JOIN general_dim_labor l ON a.id_labor = l.id
            JOIN general_dim_colaborador c ON r.id_colaborador = c.id
            LEFT JOIN general_dim_bono b ON r.id_bono = b.id
            LEFT JOIN general_dim_ceco ce ON r.id_ceco = ce.id
            WHERE a.id_sucursalactiva = %s
        """
        params = [id_sucursal]
        if id_actividad:
            sql += " AND r.id_actividad = %s"
            params.append(id_actividad)
        sql += " ORDER BY l.nombre ASC"
        cursor.execute(sql, tuple(params))
        rendimientos = cursor.fetchall()

        cursor.close()
        conn.close()

        if not rendimientos:
            return jsonify([]), 200

        return jsonify(rendimientos), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Obtener rendimientos individuales de contratistas
@rendimientos_bp.route('/individual/contratista', methods=['GET'])
@jwt_required()
def obtener_rendimientos_individuales_contratistas():
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
        id_actividad = request.args.get('id_actividad')

        sql = """
            SELECT 
                r.id,
                r.id_actividad,
                r.id_trabajador,
                r.rendimiento,
                r.id_porcentaje_individual,
                l.nombre as nombre_actividad,
                t.nombre as nombre_trabajador,
                t.apellido_paterno,
                t.apellido_materno,
                p.porcentaje,
                COALESCE(cp.id_ceco, ci.id_ceco, cm.id_ceco, cr.id_ceco, ca.id_ceco) AS id_ceco,
                COALESCE(ce.nombre, 
                    CASE 
                        WHEN a.id_tipoceco = 1 THEN (SELECT ce2.nombre FROM tarja_fact_cecoadministrativo ca2 JOIN general_dim_ceco ce2 ON ca2.id_ceco = ce2.id WHERE ca2.id_actividad = a.id LIMIT 1)
                        WHEN a.id_tipoceco = 2 THEN (SELECT ce2.nombre FROM tarja_fact_cecoproductivo cp2 JOIN general_dim_ceco ce2 ON cp2.id_ceco = ce2.id WHERE cp2.id_actividad = a.id LIMIT 1)
                        WHEN a.id_tipoceco = 3 THEN (SELECT ce2.nombre FROM tarja_fact_cecoinversion ci2 JOIN general_dim_ceco ce2 ON ci2.id_ceco = ce2.id WHERE ci2.id_actividad = a.id LIMIT 1)
                        WHEN a.id_tipoceco = 4 THEN (SELECT ce2.nombre FROM tarja_fact_cecomaquinaria cm2 JOIN general_dim_ceco ce2 ON cm2.id_ceco = ce2.id WHERE cm2.id_actividad = a.id LIMIT 1)
                        WHEN a.id_tipoceco = 5 THEN (SELECT ce2.nombre FROM tarja_fact_cecoriego cr2 JOIN general_dim_ceco ce2 ON cr2.id_ceco = ce2.id WHERE cr2.id_actividad = a.id LIMIT 1)
                    END
                ) as nombre_ceco
            FROM tarja_fact_rendimientocontratista r
            JOIN tarja_fact_actividad a ON r.id_actividad = a.id
            JOIN general_dim_labor l ON a.id_labor = l.id
            JOIN general_dim_trabajador t ON r.id_trabajador = t.id
            JOIN general_dim_porcentajecontratista p ON r.id_porcentaje_individual = p.id
            LEFT JOIN tarja_fact_cecoproductivo cp ON a.id = cp.id_actividad
            LEFT JOIN tarja_fact_cecoinversion ci ON a.id = ci.id_actividad
            LEFT JOIN tarja_fact_cecomaquinaria cm ON a.id = cm.id_actividad
            LEFT JOIN tarja_fact_cecoriego cr ON a.id = cr.id_actividad
            LEFT JOIN tarja_fact_cecoadministrativo ca ON a.id = ca.id_actividad
            LEFT JOIN general_dim_ceco ce ON COALESCE(cp.id_ceco, ci.id_ceco, cm.id_ceco, cr.id_ceco, ca.id_ceco) = ce.id
            WHERE a.id_sucursalactiva = %s
        """
        params = [id_sucursal]
        
        if id_actividad:
            sql += " AND r.id_actividad = %s"
            params.append(id_actividad)
            
        sql += " ORDER BY l.nombre ASC"
        cursor.execute(sql, tuple(params))
        rendimientos = cursor.fetchall()

        cursor.close()
        conn.close()

        if not rendimientos:
            return jsonify([]), 200

        return jsonify(rendimientos), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Obtener rendimientos grupales con porcentajes
@rendimientos_bp.route('/grupal', methods=['GET'])
@jwt_required()
def obtener_rendimientos_grupales():
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
        id_actividad = request.args.get('id_actividad')

        sql = """
            SELECT 
                rg.id,
                rg.id_actividad,
                rg.rendimiento_total,
                rg.cantidad_trab,
                rg.id_porcentaje,
                l.nombre as nombre_actividad,
                p.porcentaje as porcentaje_grupal,
                COALESCE(cp.id_ceco, ci.id_ceco, cm.id_ceco, cr.id_ceco, ca.id_ceco) AS id_ceco,
                COALESCE(ce.nombre, 
                    CASE 
                        WHEN a.id_tipoceco = 1 THEN (SELECT ce2.nombre FROM tarja_fact_cecoadministrativo ca2 JOIN general_dim_ceco ce2 ON ca2.id_ceco = ce2.id WHERE ca2.id_actividad = a.id LIMIT 1)
                        WHEN a.id_tipoceco = 2 THEN (SELECT ce2.nombre FROM tarja_fact_cecoproductivo cp2 JOIN general_dim_ceco ce2 ON cp2.id_ceco = ce2.id WHERE cp2.id_actividad = a.id LIMIT 1)
                        WHEN a.id_tipoceco = 3 THEN (SELECT ce2.nombre FROM tarja_fact_cecoinversion ci2 JOIN general_dim_ceco ce2 ON ci2.id_ceco = ce2.id WHERE ci2.id_actividad = a.id LIMIT 1)
                        WHEN a.id_tipoceco = 4 THEN (SELECT ce2.nombre FROM tarja_fact_cecomaquinaria cm2 JOIN general_dim_ceco ce2 ON cm2.id_ceco = ce2.id WHERE cm2.id_actividad = a.id LIMIT 1)
                        WHEN a.id_tipoceco = 5 THEN (SELECT ce2.nombre FROM tarja_fact_cecoriego cr2 JOIN general_dim_ceco ce2 ON cr2.id_ceco = ce2.id WHERE cr2.id_actividad = a.id LIMIT 1)
                    END
                ) as nombre_ceco
            FROM tarja_fact_redimientogrupal rg
            JOIN tarja_fact_actividad a ON rg.id_actividad = a.id
            JOIN general_dim_labor l ON a.id_labor = l.id
            LEFT JOIN general_dim_porcentajecontratista p ON rg.id_porcentaje = p.id
            LEFT JOIN tarja_fact_cecoproductivo cp ON a.id = cp.id_actividad
            LEFT JOIN tarja_fact_cecoinversion ci ON a.id = ci.id_actividad
            LEFT JOIN tarja_fact_cecomaquinaria cm ON a.id = cm.id_actividad
            LEFT JOIN tarja_fact_cecoriego cr ON a.id = cr.id_actividad
            LEFT JOIN tarja_fact_cecoadministrativo ca ON a.id = ca.id_actividad
            LEFT JOIN general_dim_ceco ce ON COALESCE(cp.id_ceco, ci.id_ceco, cm.id_ceco, cr.id_ceco, ca.id_ceco) = ce.id
            WHERE a.id_sucursalactiva = %s
        """
        params = [id_sucursal]
        
        if id_actividad:
            sql += " AND rg.id_actividad = %s"
            params.append(id_actividad)
            
        sql += " ORDER BY l.nombre ASC"
        cursor.execute(sql, tuple(params))
        rendimientos = cursor.fetchall()

        cursor.close()
        conn.close()

        if not rendimientos:
            return jsonify([]), 200

        return jsonify(rendimientos), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🚀 Endpoint para editar rendimiento individual propio
@rendimientos_bp.route('/individual/propio/<string:rendimiento_id>', methods=['PUT'])
@jwt_required()
def editar_rendimiento_individual_propio(rendimiento_id):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()

        # Calcular horas_trabajadas a partir de la actividad
        cursor.execute("SELECT hora_inicio, hora_fin FROM tarja_fact_actividad WHERE id = %s", (data['id_actividad'],))
        actividad = cursor.fetchone()
        if not actividad or not actividad[0] or not actividad[1]:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se pudo obtener hora_inicio y hora_fin de la actividad"}), 400
        hora_inicio = actividad[0]
        hora_fin = actividad[1]
        h_inicio = datetime.strptime(str(hora_inicio), "%H:%M:%S")
        h_fin = datetime.strptime(str(hora_fin), "%H:%M:%S")
        horas_trabajadas = (h_fin - h_inicio).total_seconds() / 3600
        if horas_trabajadas < 0:
            horas_trabajadas += 24

        # Asegurar que horas_extras nunca sea None
        horas_extras = data.get('horas_extras')
        if horas_extras is None:
            horas_extras = 0

        sql = """
            UPDATE tarja_fact_rendimientopropio 
            SET id_actividad = %s, id_colaborador = %s, rendimiento = %s, 
                horas_trabajadas = %s, horas_extras = %s, id_bono = %s
            WHERE id = %s
        """
        cursor.execute(sql, (
            data['id_actividad'],
            data['id_colaborador'],
            data['rendimiento'],
            horas_trabajadas,
            horas_extras,
            data.get('id_bono', None),
            rendimiento_id
        ))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Rendimiento individual propio actualizado correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para editar rendimiento individual de contratista
@rendimientos_bp.route('/individual/contratista/<string:rendimiento_id>', methods=['PUT'])
@jwt_required()
def editar_rendimiento_individual_contratista(rendimiento_id):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            UPDATE tarja_fact_rendimientocontratista 
            SET id_actividad = %s, id_trabajador = %s, rendimiento = %s, 
                id_porcentaje_individual = %s
            WHERE id = %s
        """
        cursor.execute(sql, (
            data['id_actividad'],
            data['id_trabajador'],
            data['rendimiento'],
            data['id_porcentaje_individual'],
            rendimiento_id
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento individual de contratista actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para eliminar rendimiento individual propio
@rendimientos_bp.route('/individual/propio/<string:rendimiento_id>', methods=['DELETE'])
@jwt_required()
def eliminar_rendimiento_individual_propio(rendimiento_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM tarja_fact_rendimientopropio WHERE id = %s"
        cursor.execute(sql, (rendimiento_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento individual propio eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para eliminar rendimiento individual de contratista
@rendimientos_bp.route('/individual/contratista/<string:rendimiento_id>', methods=['DELETE'])
@jwt_required()
def eliminar_rendimiento_individual_contratista(rendimiento_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM tarja_fact_rendimientocontratista WHERE id = %s"
        cursor.execute(sql, (rendimiento_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento individual de contratista eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Obtener rendimiento por ID (grupal)
@rendimientos_bp.route('/<string:rendimiento_id>', methods=['GET'])
@jwt_required()
def obtener_rendimiento(rendimiento_id):
    try:
        usuario_id = get_jwt_identity()
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
        
        # Buscar el rendimiento en las diferentes tablas
        # 1. Buscar en rendimientos propios
        cursor.execute("""
            SELECT r.*, 'propio' as tipo
            FROM tarja_fact_rendimientopropio r
            JOIN tarja_fact_actividad a ON r.id_actividad = a.id
            WHERE r.id = %s AND a.id_sucursalactiva = %s
        """, (rendimiento_id, id_sucursal))
        rendimiento = cursor.fetchone()
        
        if rendimiento:
            cursor.close()
            conn.close()
            return jsonify(rendimiento), 200
        
        # 2. Buscar en rendimientos de contratistas
        cursor.execute("""
            SELECT r.*, 'contratista' as tipo
            FROM tarja_fact_rendimientocontratista r
            JOIN tarja_fact_actividad a ON r.id_actividad = a.id
            WHERE r.id = %s AND a.id_sucursalactiva = %s
        """, (rendimiento_id, id_sucursal))
        rendimiento = cursor.fetchone()
        
        if rendimiento:
            cursor.close()
            conn.close()
            return jsonify(rendimiento), 200
        
        # 3. Buscar en rendimientos grupales
        cursor.execute("""
            SELECT r.*, 'grupal' as tipo, p.porcentaje as porcentaje_grupal
            FROM tarja_fact_redimientogrupal r
            JOIN tarja_fact_actividad a ON r.id_actividad = a.id
            LEFT JOIN general_dim_porcentajecontratista p ON r.id_porcentaje = p.id
            WHERE r.id = %s AND a.id_sucursalactiva = %s
        """, (rendimiento_id, id_sucursal))
        rendimiento = cursor.fetchone()
        
        if rendimiento:
            cursor.close()
            conn.close()
            return jsonify(rendimiento), 200
        
        cursor.close()
        conn.close()
        return jsonify({"error": "Rendimiento no encontrado"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔍 Endpoint de debug para verificar rendimientos de una actividad
@rendimientos_bp.route('/debug/<string:id_actividad>', methods=['GET'])
@jwt_required()
def debug_rendimientos_actividad(id_actividad):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar si la actividad existe
        cursor.execute("""
            SELECT id, id_tiporendimiento, id_tipotrabajador, id_labor, fecha
            FROM tarja_fact_actividad 
            WHERE id = %s
        """, (id_actividad,))
        actividad = cursor.fetchone()
        
        if not actividad:
            return jsonify({"error": "Actividad no encontrada"}), 404
        
        # Verificar rendimientos propios
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM tarja_fact_rendimientopropio 
            WHERE id_actividad = %s
        """, (id_actividad,))
        rendimientos_propios = cursor.fetchone()
        
        # Verificar rendimientos de contratistas
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM tarja_fact_rendimientocontratista 
            WHERE id_actividad = %s
        """, (id_actividad,))
        rendimientos_contratistas = cursor.fetchone()
        
        # Verificar rendimientos grupales
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM tarja_fact_redimientogrupal 
            WHERE id_actividad = %s
        """, (id_actividad,))
        rendimientos_grupales = cursor.fetchone()
        
        # Obtener detalles de la actividad
        cursor.execute("""
            SELECT 
                a.id,
                a.id_tiporendimiento,
                a.id_tipotrabajador,
                l.nombre as labor,
                a.fecha
            FROM tarja_fact_actividad a
            LEFT JOIN general_dim_labor l ON a.id_labor = l.id
            WHERE a.id = %s
        """, (id_actividad,))
        actividad_detalle = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "actividad": actividad_detalle,
            "rendimientos_propios": rendimientos_propios['total'],
            "rendimientos_contratistas": rendimientos_contratistas['total'],
            "rendimientos_grupales": rendimientos_grupales['total'],
            "total_rendimientos": (
                rendimientos_propios['total'] + 
                rendimientos_contratistas['total'] + 
                rendimientos_grupales['total']
            )
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🧪 Endpoint para crear rendimiento de prueba
@rendimientos_bp.route('/test/crear-rendimiento-propio', methods=['POST'])
@jwt_required()
def crear_rendimiento_test():
    try:
        data = request.json
        id_actividad = data.get('id_actividad')
        id_colaborador = data.get('id_colaborador')
        rendimiento = data.get('rendimiento', 100.0)
        horas_trabajadas = data.get('horas_trabajadas', 8.0)
        
        if not id_actividad or not id_colaborador:
            return jsonify({"error": "Faltan parámetros: id_actividad, id_colaborador"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que la actividad existe y es de tipo individual propio
        cursor.execute("""
            SELECT id, id_tiporendimiento, id_tipotrabajador 
            FROM tarja_fact_actividad 
            WHERE id = %s
        """, (id_actividad,))
        actividad = cursor.fetchone()
        
        if not actividad:
            return jsonify({"error": "Actividad no encontrada"}), 404
        
        if actividad['id_tiporendimiento'] != 1 or actividad['id_tipotrabajador'] != 1:
            return jsonify({"error": "La actividad debe ser de tipo individual propio"}), 400
        
        # Verificar que el colaborador existe
        cursor.execute("SELECT id FROM general_dim_colaborador WHERE id = %s", (id_colaborador,))
        colaborador = cursor.fetchone()
        
        if not colaborador:
            return jsonify({"error": "Colaborador no encontrado"}), 404
        
        # Crear rendimiento de prueba
        import uuid
        rendimiento_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO tarja_fact_rendimientopropio (
                id, id_actividad, id_colaborador, rendimiento, horas_trabajadas, horas_extras
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (rendimiento_id, id_actividad, id_colaborador, rendimiento, horas_trabajadas, 0))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Rendimiento de prueba creado correctamente",
            "rendimiento_id": rendimiento_id,
            "actividad_id": id_actividad,
            "colaborador_id": id_colaborador,
            "rendimiento": rendimiento,
            "horas_trabajadas": horas_trabajadas
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

