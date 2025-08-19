from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
import uuid
from datetime import datetime

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
                        'nombre_actividad', CONCAT('Actividad ', a.id),
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