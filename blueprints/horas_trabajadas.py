from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
import uuid
from datetime import datetime, date

horas_trabajadas_bp = Blueprint('horas_trabajadas_bp', __name__)

# Obtener resumen de horas diarias por colaborador desde rendimiento propio
@horas_trabajadas_bp.route('/resumen-diario-colaborador', methods=['GET'])
@jwt_required()
def obtener_resumen_horas_diarias_colaborador():
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
        
        # Parámetros de filtrado
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        id_colaborador = request.args.get('id_colaborador')
        
        # Construir consulta para obtener actividades agrupadas por colaborador y día
        sql = """
            SELECT 
                c.id as id_colaborador,
                CONCAT(c.nombre, ' ', c.apellido_paterno, 
                       CASE WHEN c.apellido_materno IS NOT NULL THEN CONCAT(' ', c.apellido_materno) ELSE '' END) as colaborador,
                a.fecha,
                DAYNAME(a.fecha) as nombre_dia,
                SUM(rp.horas_trabajadas) as total_horas_trabajadas,
                SUM(rp.horas_extras) as total_horas_extras,
                h.horas_dia as horas_esperadas,
                (SUM(rp.horas_trabajadas) - h.horas_dia) as diferencia_horas,
                CASE 
                    WHEN SUM(rp.horas_trabajadas) > h.horas_dia THEN 'MÁS'
                    WHEN SUM(rp.horas_trabajadas) < h.horas_dia THEN 'MENOS'
                    ELSE 'EXACTO'
                END as estado_trabajo,
                COUNT(DISTINCT a.id) as cantidad_actividades,
                JSON_ARRAYAGG(
                    JSON_OBJECT(
                        'id_actividad', a.id,
                        'rendimiento_id', rp.id,
                        'labor', l.nombre,
                        'ceco', CASE 
                            WHEN a.id_tipoceco = 1 THEN (SELECT ce.nombre FROM tarja_fact_cecoadministrativo ca JOIN general_dim_ceco ce ON ca.id_ceco = ce.id WHERE ca.id_actividad = a.id AND ca.id_ceco = rp.id_ceco LIMIT 1)
                            WHEN a.id_tipoceco = 2 THEN (SELECT ce.nombre FROM tarja_fact_cecoproductivo cp JOIN general_dim_ceco ce ON cp.id_ceco = ce.id WHERE cp.id_actividad = a.id AND cp.id_ceco = rp.id_ceco LIMIT 1)
                            WHEN a.id_tipoceco = 3 THEN (SELECT ce.nombre FROM tarja_fact_cecomaquinaria cm JOIN general_dim_ceco ce ON cm.id_ceco = ce.id WHERE cm.id_actividad = a.id AND cm.id_ceco = rp.id_ceco LIMIT 1)
                            WHEN a.id_tipoceco = 4 THEN (SELECT ce.nombre FROM tarja_fact_cecoinversion ci JOIN general_dim_ceco ce ON ci.id_ceco = ce.id WHERE ci.id_actividad = a.id AND ci.id_ceco = rp.id_ceco LIMIT 1)
                            WHEN a.id_tipoceco = 5 THEN (SELECT ce.nombre FROM tarja_fact_cecoriego cr JOIN general_dim_ceco ce ON cr.id_ceco = ce.id WHERE cr.id_actividad = a.id AND cr.id_ceco = rp.id_ceco LIMIT 1)
                            ELSE NULL
                        END,
                        'nombre_ceco', CASE 
                            WHEN a.id_tipoceco = 1 THEN (SELECT ce.nombre FROM tarja_fact_cecoadministrativo ca JOIN general_dim_ceco ce ON ca.id_ceco = ce.id WHERE ca.id_actividad = a.id AND ca.id_ceco = rp.id_ceco LIMIT 1)
                            WHEN a.id_tipoceco = 2 THEN (SELECT ce.nombre FROM tarja_fact_cecoproductivo cp JOIN general_dim_ceco ce ON cp.id_ceco = ce.id WHERE cp.id_actividad = a.id AND cp.id_ceco = rp.id_ceco LIMIT 1)
                            WHEN a.id_tipoceco = 3 THEN (SELECT ce.nombre FROM tarja_fact_cecomaquinaria cm JOIN general_dim_ceco ce ON cm.id_ceco = ce.id WHERE cm.id_actividad = a.id AND cm.id_ceco = rp.id_ceco LIMIT 1)
                            WHEN a.id_tipoceco = 4 THEN (SELECT ce.nombre FROM tarja_fact_cecoinversion ci JOIN general_dim_ceco ce ON ci.id_ceco = ce.id WHERE ci.id_actividad = a.id AND ci.id_ceco = rp.id_ceco LIMIT 1)
                            WHEN a.id_tipoceco = 5 THEN (SELECT ce.nombre FROM tarja_fact_cecoriego cr JOIN general_dim_ceco ce ON cr.id_ceco = ce.id WHERE cr.id_actividad = a.id AND cr.id_ceco = rp.id_ceco LIMIT 1)
                            ELSE NULL
                        END,
                        'id_ceco', rp.id_ceco,
                        'horas_trabajadas', rp.horas_trabajadas,
                        'horas_extras', rp.horas_extras,
                        'rendimiento', rp.rendimiento,
                        'hora_inicio', a.hora_inicio,
                        'hora_fin', a.hora_fin
                    )
                ) as actividades_detalle
            FROM tarja_fact_rendimientopropio rp
            INNER JOIN tarja_fact_actividad a ON rp.id_actividad = a.id
            INNER JOIN general_dim_colaborador c ON rp.id_colaborador = c.id
            INNER JOIN general_dim_sucursal s ON c.id_sucursal = s.id
            LEFT JOIN general_dim_labor l ON a.id_labor = l.id
            LEFT JOIN tarja_dim_horaspordia h ON h.id_empresa = s.id_empresa 
                AND h.nombre_dia = CASE 
                    WHEN DAYNAME(a.fecha) = 'Monday' THEN 'Lunes'
                    WHEN DAYNAME(a.fecha) = 'Tuesday' THEN 'Martes'
                    WHEN DAYNAME(a.fecha) = 'Wednesday' THEN 'Miércoles'
                    WHEN DAYNAME(a.fecha) = 'Thursday' THEN 'Jueves'
                    WHEN DAYNAME(a.fecha) = 'Friday' THEN 'Viernes'
                    WHEN DAYNAME(a.fecha) = 'Saturday' THEN 'Sábado'
                    WHEN DAYNAME(a.fecha) = 'Sunday' THEN 'Domingo'
                END
            WHERE c.id_sucursal = %s
        """
        params = [id_sucursal]
        
        # Agregar filtros
        if fecha_inicio:
            sql += " AND a.fecha >= %s"
            params.append(fecha_inicio)
        
        if fecha_fin:
            sql += " AND a.fecha <= %s"
            params.append(fecha_fin)
        
        if id_colaborador:
            sql += " AND c.id = %s"
            params.append(id_colaborador)
        
        # Agrupar por colaborador y fecha
        sql += " GROUP BY c.id, c.nombre, c.apellido_paterno, c.apellido_materno, a.fecha, h.horas_dia ORDER BY a.fecha DESC, c.nombre ASC"
        
        cursor.execute(sql, tuple(params))
        resultados = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(resultados), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar horas trabajadas de un colaborador
@horas_trabajadas_bp.route('/editar/<string:rendimiento_id>', methods=['PUT'])
@jwt_required()
def editar_horas_trabajadas(rendimiento_id):
    try:
        usuario_id = get_jwt_identity()
        data = request.json
        
        # Validar campos requeridos
        if 'horas_trabajadas' not in data or 'horas_extras' not in data:
            return jsonify({"error": "Los campos horas_trabajadas y horas_extras son requeridos"}), 400
        
        # Validar que las horas sean números positivos
        try:
            horas_trabajadas = float(data['horas_trabajadas'])
            horas_extras = float(data['horas_extras'])
            
            if horas_trabajadas < 0 or horas_extras < 0:
                return jsonify({"error": "Las horas deben ser valores positivos"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Las horas deben ser números válidos"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener la sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        
        if not usuario or usuario['id_sucursalactiva'] is None:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        id_sucursal = usuario['id_sucursalactiva']
        
        # Buscar el rendimiento por su ID y verificar permisos de sucursal
        cursor.execute("""
            SELECT rp.*, c.nombre as nombre_colaborador, c.apellido_paterno, c.apellido_materno,
                   a.fecha, l.nombre as labor
            FROM tarja_fact_rendimientopropio rp
            INNER JOIN general_dim_colaborador c ON rp.id_colaborador = c.id
            INNER JOIN tarja_fact_actividad a ON rp.id_actividad = a.id
            LEFT JOIN general_dim_labor l ON a.id_labor = l.id
            WHERE rp.id = %s AND c.id_sucursal = %s
        """, (rendimiento_id, id_sucursal))
        
        rendimiento = cursor.fetchone()
        if not rendimiento:
            return jsonify({"error": "Rendimiento no encontrado o no tienes permisos para editarlo"}), 404
        
        # Actualizar las horas trabajadas y extras
        cursor.execute("""
            UPDATE tarja_fact_rendimientopropio
            SET horas_trabajadas = %s, horas_extras = %s
            WHERE id = %s
        """, (horas_trabajadas, horas_extras, rendimiento_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        nombre_completo = f"{rendimiento['nombre_colaborador']} {rendimiento['apellido_paterno']} {rendimiento.get('apellido_materno', '')}".strip()
        
        return jsonify({
            "message": f"Horas trabajadas de {nombre_completo} actualizadas correctamente",
            "rendimiento_actualizado": {
                "id": rendimiento_id,
                "colaborador": nombre_completo,
                "fecha": rendimiento['fecha'].strftime('%Y-%m-%d') if isinstance(rendimiento['fecha'], (datetime, date)) else str(rendimiento['fecha']),
                "labor": rendimiento['labor'],
                "horas_trabajadas_anterior": rendimiento['horas_trabajadas'],
                "horas_extras_anterior": rendimiento['horas_extras'],
                "horas_trabajadas_nuevo": horas_trabajadas,
                "horas_extras_nuevo": horas_extras
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500