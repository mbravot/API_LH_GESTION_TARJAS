from flask import Blueprint, jsonify, request
from utils.db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

tarja_propio_bp = Blueprint('tarja_propio_bp', __name__)

@tarja_propio_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_tarjas_propios():
    """Obtener tarjas propios filtrados por sucursal del usuario"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener información del usuario autenticado
        cursor.execute("""
            SELECT id_sucursalactiva FROM general_dim_usuario 
            WHERE id = %s
        """, (get_jwt_identity(),))
        usuario = cursor.fetchone()
        
        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404
            
        id_sucursal = usuario['id_sucursalactiva']
        
        # Obtener parámetros de consulta opcionales
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')
        id_colaborador = request.args.get('id_colaborador')
        id_labor = request.args.get('id_labor')
        id_ceco = request.args.get('id_ceco')
        id_estadoactividad = request.args.get('id_estadoactividad')
        
        # Construir query base
        query = """
            SELECT 
                id_sucursal,
                fecha,
                id_usuario,
                usuario,
                id_colaborador,
                colaborador,
                id_labor,
                labor,
                id_tiporendimiento,
                tipo_renimiento,
                id_ceco,
                centro_de_costo,
                detalle_ceco,
                horas_trabajadas,
                id_unidad,
                unidad,
                rendimiento,
                tarifa,
                liquido_trato_dia,
                horas_extras,
                valor_he,
                total_HE,
                id_estadoactividad,
                estado
            FROM v_tarja_tarjaweb_tarjaspropios
            WHERE id_sucursal = %s
        """
        
        params = [id_sucursal]
        
        # Agregar filtros opcionales
        if fecha_desde:
            query += " AND fecha >= %s"
            params.append(fecha_desde)
            
        if fecha_hasta:
            query += " AND fecha <= %s"
            params.append(fecha_hasta)
            
        if id_colaborador:
            query += " AND id_colaborador = %s"
            params.append(id_colaborador)
            
        if id_labor:
            query += " AND id_labor = %s"
            params.append(id_labor)
            
        if id_ceco:
            query += " AND id_ceco = %s"
            params.append(id_ceco)
            
        if id_estadoactividad:
            query += " AND id_estadoactividad = %s"
            params.append(id_estadoactividad)
        
        # Ordenar por fecha descendente
        query += " ORDER BY fecha DESC, colaborador ASC"
        
        cursor.execute(query, params)
        tarjas = cursor.fetchall()
        
        # Convertir campos de tiempo a string para evitar errores de serialización JSON
        for tarja in tarjas:
            if tarja.get('horas_trabajadas'):
                tarja['horas_trabajadas'] = str(tarja['horas_trabajadas'])
            if tarja.get('horas_extras'):
                tarja['horas_extras'] = str(tarja['horas_extras'])
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "tarjas_propios": tarjas,
            "total": len(tarjas)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@tarja_propio_bp.route('/resumen', methods=['GET'])
@jwt_required()
def obtener_resumen_tarjas_propios():
    """Obtener resumen de tarjas propios por colaborador"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener información del usuario autenticado
        cursor.execute("""
            SELECT id_sucursalactiva FROM general_dim_usuario 
            WHERE id = %s
        """, (get_jwt_identity(),))
        usuario = cursor.fetchone()
        
        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404
            
        id_sucursal = usuario['id_sucursalactiva']
        
        # Obtener parámetros de consulta opcionales
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')
        
        # Construir query de resumen
        query = """
            SELECT 
                id_colaborador,
                colaborador,
                COUNT(*) as total_registros,
                SUM(horas_trabajadas) as total_horas_trabajadas,
                SUM(rendimiento) as total_rendimiento,
                SUM(horas_extras) as total_horas_extras,
                SUM(valor_he) as total_valor_he,
                SUM(liquido_trato_dia) as total_liquido_trato_dia,
                AVG(rendimiento) as promedio_rendimiento
            FROM v_tarja_tarjaweb_tarjaspropios
            WHERE id_sucursal = %s
        """
        
        params = [id_sucursal]
        
        # Agregar filtros de fecha si se proporcionan
        if fecha_desde:
            query += " AND fecha >= %s"
            params.append(fecha_desde)
            
        if fecha_hasta:
            query += " AND fecha <= %s"
            params.append(fecha_hasta)
        
        query += " GROUP BY id_colaborador, colaborador ORDER BY colaborador ASC"
        
        cursor.execute(query, params)
        resumen = cursor.fetchall()
        
        # Convertir campos de tiempo a string para evitar errores de serialización JSON
        for item in resumen:
            if item.get('total_horas_trabajadas'):
                item['total_horas_trabajadas'] = str(item['total_horas_trabajadas'])
            if item.get('total_horas_extras'):
                item['total_horas_extras'] = str(item['total_horas_extras'])
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "resumen": resumen,
            "total_colaboradores": len(resumen)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
