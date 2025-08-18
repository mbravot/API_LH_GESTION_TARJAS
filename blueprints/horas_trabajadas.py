from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
import uuid
from datetime import datetime

horas_trabajadas_bp = Blueprint('horas_trabajadas_bp', __name__)

# Obtener resumen de horas diarias por colaborador vs horas esperadas
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
        
        # Construir consulta de resumen diario usando id_sucursal directamente de la vista
        sql = """
            SELECT 
                v.id_colaborador,
                v.colaborador,
                v.fecha,
                DAYNAME(v.fecha) as nombre_dia,
                SUM(v.horas_trabajadas) as horas_trabajadas,
                h.horas_dia as horas_esperadas,
                (SUM(v.horas_trabajadas) - h.horas_dia) as diferencia_horas,
                CASE 
                    WHEN SUM(v.horas_trabajadas) > h.horas_dia THEN 'MÁS'
                    WHEN SUM(v.horas_trabajadas) < h.horas_dia THEN 'MENOS'
                    ELSE 'EXACTO'
                END as estado_trabajo
            FROM v_tarja_tarjamovil_controlhoras v
            LEFT JOIN tarja_dim_horaspordia h ON h.id_empresa = v.id_empresa 
                AND h.nombre_dia = CASE 
                    WHEN DAYNAME(v.fecha) = 'Monday' THEN 'Lunes'
                    WHEN DAYNAME(v.fecha) = 'Tuesday' THEN 'Martes'
                    WHEN DAYNAME(v.fecha) = 'Wednesday' THEN 'Miércoles'
                    WHEN DAYNAME(v.fecha) = 'Thursday' THEN 'Jueves'
                    WHEN DAYNAME(v.fecha) = 'Friday' THEN 'Viernes'
                    WHEN DAYNAME(v.fecha) = 'Saturday' THEN 'Sábado'
                    WHEN DAYNAME(v.fecha) = 'Sunday' THEN 'Domingo'
                END
            WHERE v.id_sucursal = %s
                AND v.id_usuario = %s
        """
        params = [id_sucursal, usuario_id]
        
        # Agregar filtros
        if fecha_inicio:
            sql += " AND v.fecha >= %s"
            params.append(fecha_inicio)
        
        if fecha_fin:
            sql += " AND v.fecha <= %s"
            params.append(fecha_fin)
        
        if id_colaborador:
            sql += " AND v.id_colaborador = %s"
            params.append(id_colaborador)
        
        # Agrupar por colaborador y fecha
        sql += " GROUP BY v.id_colaborador, v.colaborador, v.fecha, h.horas_dia ORDER BY v.fecha DESC, v.colaborador ASC"
        
        cursor.execute(sql, tuple(params))
        resultados = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(resultados), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500