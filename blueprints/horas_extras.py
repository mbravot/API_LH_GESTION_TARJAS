from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
import uuid
from datetime import datetime

horas_extras_bp = Blueprint('horas_extras_bp', __name__)

# Listar rendimientos propios agrupados por colaborador y día
@horas_extras_bp.route('/rendimientos', methods=['GET'])
@jwt_required()
def listar_rendimientos_propios():
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
        
        # Parámetros de filtrado
        id_colaborador = request.args.get('id_colaborador')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        # Construir query para obtener actividades agrupadas por colaborador y día
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
                        'id_rendimiento', rp.id,
                        'id_actividad', a.id,
                        'labor', l.nombre,
                        'ceco', CASE 
                            WHEN rp.id_ceco IS NOT NULL THEN (SELECT ce.nombre FROM general_dim_ceco ce WHERE ce.id = rp.id_ceco)
                            WHEN a.id_tipoceco = 1 THEN (SELECT ce.nombre FROM tarja_fact_cecoadministrativo ca JOIN general_dim_ceco ce ON ca.id_ceco = ce.id WHERE ca.id_actividad = a.id LIMIT 1)
                            WHEN a.id_tipoceco = 2 THEN (SELECT ce.nombre FROM tarja_fact_cecoproductivo cp JOIN general_dim_ceco ce ON cp.id_ceco = ce.id WHERE cp.id_actividad = a.id LIMIT 1)
                            WHEN a.id_tipoceco = 3 THEN (SELECT ce.nombre FROM tarja_fact_cecomaquinaria cm JOIN general_dim_ceco ce ON cm.id_ceco = ce.id WHERE cm.id_actividad = a.id LIMIT 1)
                            WHEN a.id_tipoceco = 4 THEN (SELECT ce.nombre FROM tarja_fact_cecoinversion ci JOIN general_dim_ceco ce ON ci.id_ceco = ce.id WHERE ci.id_actividad = a.id LIMIT 1)
                            WHEN a.id_tipoceco = 5 THEN (SELECT ce.nombre FROM tarja_fact_cecoriego cr JOIN general_dim_ceco ce ON cr.id_ceco = ce.id WHERE cr.id_actividad = a.id LIMIT 1)
                            ELSE NULL
                        END,
                        'nombre_ceco', CASE 
                            WHEN rp.id_ceco IS NOT NULL THEN (SELECT ce.nombre FROM general_dim_ceco ce WHERE ce.id = rp.id_ceco)
                            WHEN a.id_tipoceco = 1 THEN (SELECT ce.nombre FROM tarja_fact_cecoadministrativo ca JOIN general_dim_ceco ce ON ca.id_ceco = ce.id WHERE ca.id_actividad = a.id LIMIT 1)
                            WHEN a.id_tipoceco = 2 THEN (SELECT ce.nombre FROM tarja_fact_cecoproductivo cp JOIN general_dim_ceco ce ON cp.id_ceco = ce.id WHERE cp.id_actividad = a.id LIMIT 1)
                            WHEN a.id_tipoceco = 3 THEN (SELECT ce.nombre FROM tarja_fact_cecomaquinaria cm JOIN general_dim_ceco ce ON cm.id_ceco = ce.id WHERE cm.id_actividad = a.id LIMIT 1)
                            WHEN a.id_tipoceco = 4 THEN (SELECT ce.nombre FROM tarja_fact_cecoinversion ci JOIN general_dim_ceco ce ON ci.id_ceco = ce.id WHERE ci.id_actividad = a.id LIMIT 1)
                            WHEN a.id_tipoceco = 5 THEN (SELECT ce.nombre FROM tarja_fact_cecoriego cr JOIN general_dim_ceco ce ON cr.id_ceco = ce.id WHERE cr.id_actividad = a.id LIMIT 1)
                            ELSE NULL
                        END,
                        'id_ceco', COALESCE(rp.id_ceco, 
                            CASE 
                                WHEN a.id_tipoceco = 1 THEN (SELECT ca.id_ceco FROM tarja_fact_cecoadministrativo ca WHERE ca.id_actividad = a.id LIMIT 1)
                                WHEN a.id_tipoceco = 2 THEN (SELECT cp.id_ceco FROM tarja_fact_cecoproductivo cp WHERE cp.id_actividad = a.id LIMIT 1)
                                WHEN a.id_tipoceco = 3 THEN (SELECT cm.id_ceco FROM tarja_fact_cecomaquinaria cm WHERE cm.id_actividad = a.id LIMIT 1)
                                WHEN a.id_tipoceco = 4 THEN (SELECT ci.id_ceco FROM tarja_fact_cecoinversion ci WHERE ci.id_actividad = a.id LIMIT 1)
                                WHEN a.id_tipoceco = 5 THEN (SELECT cr.id_ceco FROM tarja_fact_cecoriego cr WHERE cr.id_actividad = a.id LIMIT 1)
                                ELSE NULL
                            END),
                        'horas_trabajadas', rp.horas_trabajadas,
                        'horas_extras', rp.horas_extras,
                        'rendimiento', rp.rendimiento,
                        'hora_inicio', a.hora_inicio,
                        'hora_fin', a.hora_fin,
                        'id_bono', rp.id_bono,
                        'nombre_bono', b.nombre
                    )
                ) as actividades_detalle
            FROM tarja_fact_rendimientopropio rp
            INNER JOIN tarja_fact_actividad a ON rp.id_actividad = a.id
            INNER JOIN general_dim_colaborador c ON rp.id_colaborador = c.id
            INNER JOIN general_dim_sucursal s ON c.id_sucursal = s.id
            LEFT JOIN general_dim_labor l ON a.id_labor = l.id
            LEFT JOIN general_dim_bono b ON rp.id_bono = b.id
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
        rendimientos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(rendimientos), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener rendimiento propio por ID
@horas_extras_bp.route('/rendimientos/<string:rendimiento_id>', methods=['GET'])
@jwt_required()
def obtener_rendimiento_propio(rendimiento_id):
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
        
        # Obtener rendimiento específico
        cursor.execute("""
            SELECT 
                rp.id,
                rp.id_actividad,
                rp.id_colaborador,
                rp.rendimiento,
                rp.horas_trabajadas,
                rp.horas_extras,
                rp.id_bono,
                l.nombre as labor,
                CASE 
                    WHEN a.id_tipoceco = 1 THEN (SELECT ce.nombre FROM tarja_fact_cecoadministrativo ca JOIN general_dim_ceco ce ON ca.id_ceco = ce.id WHERE ca.id_actividad = a.id LIMIT 1)
                    WHEN a.id_tipoceco = 2 THEN (SELECT ce.nombre FROM tarja_fact_cecoproductivo cp JOIN general_dim_ceco ce ON cp.id_ceco = ce.id WHERE cp.id_actividad = a.id LIMIT 1)
                    WHEN a.id_tipoceco = 3 THEN (SELECT ce.nombre FROM tarja_fact_cecomaquinaria cm JOIN general_dim_ceco ce ON cm.id_ceco = ce.id WHERE cm.id_actividad = a.id LIMIT 1)
                    WHEN a.id_tipoceco = 4 THEN (SELECT ce.nombre FROM tarja_fact_cecoinversion ci JOIN general_dim_ceco ce ON ci.id_ceco = ce.id WHERE ci.id_actividad = a.id LIMIT 1)
                    WHEN a.id_tipoceco = 5 THEN (SELECT ce.nombre FROM tarja_fact_cecoriego cr JOIN general_dim_ceco ce ON cr.id_ceco = ce.id WHERE cr.id_actividad = a.id LIMIT 1)
                    ELSE NULL
                END as ceco,
                a.fecha as fecha_actividad,
                c.nombre as nombre_colaborador,
                c.apellido_paterno,
                c.apellido_materno,
                b.nombre as nombre_bono
            FROM tarja_fact_rendimientopropio rp
            INNER JOIN tarja_fact_actividad a ON rp.id_actividad = a.id
            INNER JOIN general_dim_colaborador c ON rp.id_colaborador = c.id
            LEFT JOIN general_dim_labor l ON a.id_labor = l.id
            LEFT JOIN general_dim_bono b ON rp.id_bono = b.id
            WHERE rp.id = %s AND c.id_sucursal = %s
        """, (rendimiento_id, id_sucursal))
        
        rendimiento = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not rendimiento:
            return jsonify({"error": "Rendimiento no encontrado"}), 404
        
        return jsonify(rendimiento), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Asignar horas extras a un rendimiento
@horas_extras_bp.route('/rendimientos/<string:rendimiento_id>/horas-extras', methods=['PUT'])
@jwt_required()
def asignar_horas_extras(rendimiento_id):
    try:
        data = request.json
        usuario_id = get_jwt_identity()
        
        # Validar campos requeridos
        if 'horas_extras' not in data:
            return jsonify({"error": "Campo requerido faltante: horas_extras"}), 400
        
        horas_extras = data['horas_extras']
        if not isinstance(horas_extras, (int, float)) or horas_extras < 0:
            return jsonify({"error": "horas_extras debe ser un número positivo"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        id_sucursal = usuario['id_sucursalactiva']
        
        # Verificar que el rendimiento existe y pertenece a la sucursal
        cursor.execute("""
            SELECT rp.id FROM tarja_fact_rendimientopropio rp
            INNER JOIN general_dim_colaborador c ON rp.id_colaborador = c.id
            WHERE rp.id = %s AND c.id_sucursal = %s
        """, (rendimiento_id, id_sucursal))
        
        if not cursor.fetchone():
            return jsonify({"error": "Rendimiento no encontrado"}), 404
        
        # Actualizar horas extras
        cursor.execute("""
            UPDATE tarja_fact_rendimientopropio 
            SET horas_extras = %s
            WHERE id = %s
        """, (horas_extras, rendimiento_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Horas extras asignadas correctamente"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener actividades por colaborador y sucursal
@horas_extras_bp.route('/actividades-colaborador/<string:id_colaborador>', methods=['GET'])
@jwt_required()
def obtener_actividades_colaborador(id_colaborador):
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
        
        # Verificar que el colaborador pertenece a la sucursal
        cursor.execute("""
            SELECT id FROM general_dim_colaborador 
            WHERE id = %s AND id_sucursal = %s
        """, (id_colaborador, id_sucursal))
        
        if not cursor.fetchone():
            return jsonify({"error": "Colaborador no encontrado"}), 404
        
        # Obtener actividades del colaborador
        cursor.execute("""
            SELECT 
                a.id,
                l.nombre as labor,
                a.fecha,
                CASE 
                    WHEN a.id_tipoceco = 1 THEN (SELECT ce.nombre FROM tarja_fact_cecoadministrativo ca JOIN general_dim_ceco ce ON ca.id_ceco = ce.id WHERE ca.id_actividad = a.id LIMIT 1)
                    WHEN a.id_tipoceco = 2 THEN (SELECT ce.nombre FROM tarja_fact_cecoproductivo cp JOIN general_dim_ceco ce ON cp.id_ceco = ce.id WHERE cp.id_actividad = a.id LIMIT 1)
                    WHEN a.id_tipoceco = 3 THEN (SELECT ce.nombre FROM tarja_fact_cecomaquinaria cm JOIN general_dim_ceco ce ON cm.id_ceco = ce.id WHERE cm.id_actividad = a.id LIMIT 1)
                    WHEN a.id_tipoceco = 4 THEN (SELECT ce.nombre FROM tarja_fact_cecoinversion ci JOIN general_dim_ceco ce ON ci.id_ceco = ce.id WHERE ci.id_actividad = a.id LIMIT 1)
                    WHEN a.id_tipoceco = 5 THEN (SELECT ce.nombre FROM tarja_fact_cecoriego cr JOIN general_dim_ceco ce ON cr.id_ceco = ce.id WHERE cr.id_actividad = a.id LIMIT 1)
                    ELSE NULL
                END as ceco,
                rp.id as rendimiento_id,
                rp.rendimiento,
                rp.horas_trabajadas,
                rp.horas_extras
            FROM tarja_fact_actividad a
            LEFT JOIN general_dim_labor l ON a.id_labor = l.id
            LEFT JOIN tarja_fact_rendimientopropio rp ON a.id = rp.id_actividad AND rp.id_colaborador = %s
            WHERE a.id_usuario = %s
            ORDER BY a.fecha DESC
        """, (id_colaborador, id_colaborador))
        
        actividades = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(actividades), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Crear nuevo rendimiento propio con horas extras
@horas_extras_bp.route('/rendimientos', methods=['POST'])
@jwt_required()
def crear_rendimiento_propio():
    try:
        data = request.json
        usuario_id = get_jwt_identity()
        
        # Validar campos requeridos
        campos_requeridos = ['id_actividad', 'id_colaborador', 'rendimiento', 'horas_trabajadas']
        for campo in campos_requeridos:
            if not data.get(campo):
                return jsonify({"error": f"Campo requerido faltante: {campo}"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        id_sucursal = usuario['id_sucursalactiva']
        
        # Verificar que el colaborador pertenece a la sucursal
        cursor.execute("""
            SELECT id FROM general_dim_colaborador 
            WHERE id = %s AND id_sucursal = %s
        """, (data['id_colaborador'], id_sucursal))
        
        if not cursor.fetchone():
            return jsonify({"error": "Colaborador no encontrado o no pertenece a tu sucursal"}), 404
        
        # Verificar que la actividad existe
        cursor.execute("""
            SELECT id FROM tarja_fact_actividad 
            WHERE id = %s
        """, (data['id_actividad'],))
        
        if not cursor.fetchone():
            return jsonify({"error": "Actividad no encontrada"}), 404
        
        # Verificar que no existe ya un rendimiento para esta actividad y colaborador
        cursor.execute("""
            SELECT id FROM tarja_fact_rendimientopropio 
            WHERE id_actividad = %s AND id_colaborador = %s
        """, (data['id_actividad'], data['id_colaborador']))
        
        if cursor.fetchone():
            return jsonify({"error": "Ya existe un rendimiento para esta actividad y colaborador"}), 400
        
        # Generar ID único
        rendimiento_id = str(uuid.uuid4())
        
        # Crear rendimiento
        sql = """
            INSERT INTO tarja_fact_rendimientopropio (
                id, id_actividad, id_colaborador, rendimiento, horas_trabajadas, horas_extras, id_bono
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(sql, (
            rendimiento_id,
            data['id_actividad'],
            data['id_colaborador'],
            data['rendimiento'],
            data['horas_trabajadas'],
            data.get('horas_extras', 0),
            data.get('id_bono')
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Rendimiento creado correctamente", "id": rendimiento_id}), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener bonos disponibles
@horas_extras_bp.route('/bonos', methods=['GET'])
@jwt_required()
def obtener_bonos():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id, nombre FROM general_dim_bono ORDER BY nombre ASC")
        bonos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(bonos), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
