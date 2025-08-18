from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
import uuid
from datetime import datetime

vacaciones_bp = Blueprint('vacaciones_bp', __name__)

def calcular_dias_habiles(fecha_inicio, fecha_fin, cursor):
    """
    Calcula los días hábiles entre dos fechas usando la tabla general_dim_fecha
    SOLO cuenta días marcados como 'dia habil' (excluye fines de semana y festivos)
    """
    try:
        # Convertir fechas a formato date si vienen como datetime
        if hasattr(fecha_inicio, 'date'):
            fecha_inicio = fecha_inicio.date()
        if hasattr(fecha_fin, 'date'):
            fecha_fin = fecha_fin.date()
        
        print(f"DEBUG - Calculando días hábiles de {fecha_inicio} a {fecha_fin}")
        
        # Verificar si hay datos en el rango
        cursor.execute("""
            SELECT COUNT(*) as total_dias
            FROM general_dim_fecha 
            WHERE fecha BETWEEN %s AND %s
        """, (fecha_inicio, fecha_fin))
        
        total_dias = cursor.fetchone()['total_dias']
        print(f"DEBUG - Total días en rango: {total_dias}")
        
        if total_dias == 0:
            print(f"DEBUG - No hay datos en la tabla para el rango {fecha_inicio} a {fecha_fin}")
            print(f"DEBUG - Retornando 0 días hábiles (no se puede calcular sin datos de la tabla)")
            return 0
        
        # Verificar qué categorías existen en el rango
        cursor.execute("""
            SELECT DISTINCT categoria, COUNT(*) as cantidad
            FROM general_dim_fecha 
            WHERE fecha BETWEEN %s AND %s
            GROUP BY categoria
        """, (fecha_inicio, fecha_fin))
        
        categorias = cursor.fetchall()
        print(f"DEBUG - Categorías encontradas: {categorias}")
        
        # Buscar SOLO días hábiles usando la categoría 'dia habil'
        cursor.execute("""
            SELECT COUNT(*) as dias_habiles
            FROM general_dim_fecha 
            WHERE fecha BETWEEN %s AND %s AND categoria = 'dia habil'
        """, (fecha_inicio, fecha_fin))
        
        resultado = cursor.fetchone()
        dias_habiles = resultado['dias_habiles'] if resultado else 0
        
        print(f"DEBUG - Días hábiles encontrados (categoría 'dia habil'): {dias_habiles}")
        
        # Si no encuentra con 'dia habil', probar con otras variaciones similares
        if dias_habiles == 0:
            print(f"DEBUG - Probando otras categorías similares...")
            cursor.execute("""
                SELECT COUNT(*) as dias_habiles
                FROM general_dim_fecha 
                WHERE fecha BETWEEN %s AND %s 
                AND (categoria LIKE '%habil%' OR categoria LIKE '%laboral%' OR categoria LIKE '%trabajo%')
            """, (fecha_inicio, fecha_fin))
            
            resultado = cursor.fetchone()
            dias_habiles = resultado['dias_habiles'] if resultado else 0
            print(f"DEBUG - Días hábiles con LIKE: {dias_habiles}")
        
        # Si no encuentra datos en la tabla, usar fallback que al menos excluye fines de semana
        # pero con advertencia de que no excluye festivos
        if dias_habiles == 0:
            print(f"DEBUG - No se encontraron días hábiles en la tabla de fechas")
            print(f"DEBUG - Usando fallback que excluye solo fines de semana (NO excluye festivos)")
            
            from datetime import timedelta
            
            dias_habiles = 0
            fecha_actual = fecha_inicio
            
            while fecha_actual <= fecha_fin:
                # Lunes = 0, Domingo = 6
                if fecha_actual.weekday() < 5:  # Lunes a Viernes
                    dias_habiles += 1
                fecha_actual += timedelta(days=1)
            
            print(f"DEBUG - Días hábiles calculados por semana (fallback): {dias_habiles}")
            print(f"DEBUG - ADVERTENCIA: Este cálculo NO excluye festivos, solo fines de semana")
        
        print(f"DEBUG - Días hábiles finales: {dias_habiles}")
        return dias_habiles
        
    except Exception as e:
        print(f"ERROR - Error calculando días hábiles: {e}")
        return 0

# Listar vacaciones de colaboradores (por sucursal activa del usuario)
@vacaciones_bp.route('', methods=['GET'])
@jwt_required()
def listar_vacaciones():
    try:
        usuario_id = get_jwt_identity()
        id_colaborador = request.args.get('id_colaborador')  # Filtro opcional por colaborador
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        id_sucursal = usuario['id_sucursalactiva']
        
        # Construir query base
        base_query = """
            SELECT 
                v.id,
                v.id_colaborador,
                v.fecha_inicio,
                v.fecha_fin,
                c.nombre as nombre_colaborador,
                c.apellido_paterno,
                c.apellido_materno,
                c.id_sucursal
            FROM tarja_fact_vacaciones v
            INNER JOIN general_dim_colaborador c ON v.id_colaborador = c.id
            WHERE c.id_sucursal = %s
        """
        params = [id_sucursal]
        
        # Agregar filtro por colaborador si se especifica
        if id_colaborador:
            base_query += " AND v.id_colaborador = %s"
            params.append(id_colaborador)
        
        base_query += " ORDER BY v.fecha_inicio DESC"
        
        cursor.execute(base_query, tuple(params))
        vacaciones = cursor.fetchall()
        
        # Calcular días hábiles para cada vacación
        for vacacion in vacaciones:
            dias_habiles = calcular_dias_habiles(vacacion['fecha_inicio'], vacacion['fecha_fin'], cursor)
            vacacion['dias_habiles'] = dias_habiles
        
        cursor.close()
        conn.close()
        
        return jsonify(vacaciones), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener vacaciones por ID
@vacaciones_bp.route('/<int:vacacion_id>', methods=['GET'])
@jwt_required()
def obtener_vacacion_por_id(vacacion_id):
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
        
        # Obtener vacación con información del colaborador
        cursor.execute("""
            SELECT 
                v.id,
                v.id_colaborador,
                v.fecha_inicio,
                v.fecha_fin,
                c.nombre as nombre_colaborador,
                c.apellido_paterno,
                c.apellido_materno,
                c.id_sucursal
            FROM tarja_fact_vacaciones v
            INNER JOIN general_dim_colaborador c ON v.id_colaborador = c.id
            WHERE v.id = %s AND c.id_sucursal = %s
        """, (vacacion_id, id_sucursal))
        
        vacacion = cursor.fetchone()
        
        if not vacacion:
            cursor.close()
            conn.close()
            return jsonify({"error": "Vacación no encontrada"}), 404
        
        # Calcular días hábiles
        dias_habiles = calcular_dias_habiles(vacacion['fecha_inicio'], vacacion['fecha_fin'], cursor)
        vacacion['dias_habiles'] = dias_habiles
        
        cursor.close()
        conn.close()
            
        return jsonify(vacacion), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Crear vacación
@vacaciones_bp.route('/', methods=['POST'])
@jwt_required()
def crear_vacacion():
    try:
        data = request.json
        usuario_id = get_jwt_identity()
        
        # Validar campos requeridos
        if not data.get('id_colaborador') or not data.get('fecha_inicio') or not data.get('fecha_fin'):
            return jsonify({"error": "Faltan campos requeridos: id_colaborador, fecha_inicio, fecha_fin"}), 400
        
        # Validar formato de fechas
        try:
            fecha_inicio = datetime.strptime(data['fecha_inicio'], '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(data['fecha_fin'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}), 400
        
        # Validar que fecha_fin sea posterior a fecha_inicio
        if fecha_fin <= fecha_inicio:
            return jsonify({"error": "La fecha de fin debe ser posterior a la fecha de inicio"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        id_sucursal = usuario['id_sucursalactiva']
        
        # Verificar que el colaborador existe y pertenece a la sucursal
        cursor.execute("""
            SELECT id FROM general_dim_colaborador 
            WHERE id = %s AND id_sucursal = %s
        """, (data['id_colaborador'], id_sucursal))
        
        colaborador = cursor.fetchone()
        if not colaborador:
            return jsonify({"error": "Colaborador no encontrado o no pertenece a la sucursal"}), 404
        
        # Verificar que no haya solapamiento de fechas
        cursor.execute("""
            SELECT id FROM tarja_fact_vacaciones 
            WHERE id_colaborador = %s AND (
                (fecha_inicio <= %s AND fecha_fin >= %s) OR
                (fecha_inicio <= %s AND fecha_fin >= %s) OR
                (fecha_inicio >= %s AND fecha_fin <= %s)
            )
        """, (data['id_colaborador'], fecha_inicio, fecha_inicio, fecha_fin, fecha_fin, fecha_inicio, fecha_fin))
        
        if cursor.fetchone():
            return jsonify({"error": "Ya existe un período de vacaciones que se solapa con las fechas especificadas"}), 400
        
        # Crear vacación
        sql = """
            INSERT INTO tarja_fact_vacaciones (id_colaborador, fecha_inicio, fecha_fin)
            VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (data['id_colaborador'], fecha_inicio, fecha_fin))
        
        vacacion_id = cursor.lastrowid
        
        # Calcular días hábiles
        dias_habiles = calcular_dias_habiles(fecha_inicio, fecha_fin, cursor)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Vacación creada correctamente", 
            "id": vacacion_id,
            "dias_habiles": dias_habiles
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar vacación
@vacaciones_bp.route('/<int:vacacion_id>', methods=['PUT'])
@jwt_required()
def editar_vacacion(vacacion_id):
    try:
        data = request.json
        usuario_id = get_jwt_identity()
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        id_sucursal = usuario['id_sucursalactiva']
        
        # Obtener vacación actual
        cursor.execute("""
            SELECT v.*, c.id_sucursal
            FROM tarja_fact_vacaciones v
            INNER JOIN general_dim_colaborador c ON v.id_colaborador = c.id
            WHERE v.id = %s AND c.id_sucursal = %s
        """, (vacacion_id, id_sucursal))
        
        vacacion_actual = cursor.fetchone()
        if not vacacion_actual:
            return jsonify({"error": "Vacación no encontrada"}), 404
        
        # Validar y procesar fechas si se proporcionan
        fecha_inicio = vacacion_actual['fecha_inicio']
        fecha_fin = vacacion_actual['fecha_fin']
        
        if 'fecha_inicio' in data:
            try:
                fecha_inicio = datetime.strptime(data['fecha_inicio'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({"error": "Formato de fecha_inicio inválido. Use YYYY-MM-DD"}), 400
        
        if 'fecha_fin' in data:
            try:
                fecha_fin = datetime.strptime(data['fecha_fin'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({"error": "Formato de fecha_fin inválido. Use YYYY-MM-DD"}), 400
        
        # Validar que fecha_fin sea posterior a fecha_inicio
        if fecha_fin <= fecha_inicio:
            return jsonify({"error": "La fecha de fin debe ser posterior a la fecha de inicio"}), 400
        
        # Verificar que no haya solapamiento de fechas (excluyendo la vacación actual)
        cursor.execute("""
            SELECT id FROM tarja_fact_vacaciones 
            WHERE id_colaborador = %s AND id != %s AND (
                (fecha_inicio <= %s AND fecha_fin >= %s) OR
                (fecha_inicio <= %s AND fecha_fin >= %s) OR
                (fecha_inicio >= %s AND fecha_fin <= %s)
            )
        """, (vacacion_actual['id_colaborador'], vacacion_id, fecha_inicio, fecha_inicio, fecha_fin, fecha_fin, fecha_inicio, fecha_fin))
        
        if cursor.fetchone():
            return jsonify({"error": "Ya existe un período de vacaciones que se solapa con las fechas especificadas"}), 400
        
        # Actualizar vacación
        sql = """
            UPDATE tarja_fact_vacaciones
            SET fecha_inicio = %s, fecha_fin = %s
            WHERE id = %s
        """
        cursor.execute(sql, (fecha_inicio, fecha_fin, vacacion_id))
        
        # Calcular días hábiles
        dias_habiles = calcular_dias_habiles(fecha_inicio, fecha_fin, cursor)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Vacación actualizada correctamente",
            "dias_habiles": dias_habiles
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Eliminar vacación
@vacaciones_bp.route('/<int:vacacion_id>', methods=['DELETE'])
@jwt_required()
def eliminar_vacacion(vacacion_id):
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
        
        # Verificar que la vacación existe y pertenece a un colaborador de la sucursal
        cursor.execute("""
            SELECT v.id
            FROM tarja_fact_vacaciones v
            INNER JOIN general_dim_colaborador c ON v.id_colaborador = c.id
            WHERE v.id = %s AND c.id_sucursal = %s
        """, (vacacion_id, id_sucursal))
        
        if not cursor.fetchone():
            return jsonify({"error": "Vacación no encontrada"}), 404
        
        # Eliminar vacación
        cursor.execute("DELETE FROM tarja_fact_vacaciones WHERE id = %s", (vacacion_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Vacación eliminada correctamente"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener vacaciones de un colaborador específico
@vacaciones_bp.route('/colaborador/<string:id_colaborador>', methods=['GET'])
@jwt_required()
def obtener_vacaciones_colaborador(id_colaborador):
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
        
        # Obtener vacaciones del colaborador
        cursor.execute("""
            SELECT 
                v.id,
                v.id_colaborador,
                v.fecha_inicio,
                v.fecha_fin,
                c.nombre as nombre_colaborador,
                c.apellido_paterno,
                c.apellido_materno,
                c.id_sucursal
            FROM tarja_fact_vacaciones v
            INNER JOIN general_dim_colaborador c ON v.id_colaborador = c.id
            WHERE v.id_colaborador = %s AND c.id_sucursal = %s
            ORDER BY v.fecha_inicio DESC
        """, (id_colaborador, id_sucursal))
        
        vacaciones = cursor.fetchall()
        
        # Calcular días hábiles para cada vacación
        for vacacion in vacaciones:
            dias_habiles = calcular_dias_habiles(vacacion['fecha_inicio'], vacacion['fecha_fin'], cursor)
            vacacion['dias_habiles'] = dias_habiles
        
        cursor.close()
        conn.close()
        
        return jsonify(vacaciones), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Calcular días hábiles de un rango de fechas
@vacaciones_bp.route('/calcular-dias-habiles', methods=['POST'])
@jwt_required()
def calcular_dias_habiles_rango():
    try:
        data = request.json
        
        # Validar campos requeridos
        if not data.get('fecha_inicio') or not data.get('fecha_fin'):
            return jsonify({"error": "Faltan campos requeridos: fecha_inicio, fecha_fin"}), 400
        
        # Validar formato de fechas
        try:
            fecha_inicio = datetime.strptime(data['fecha_inicio'], '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(data['fecha_fin'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}), 400
        
        # Validar que fecha_fin sea posterior a fecha_inicio
        if fecha_fin <= fecha_inicio:
            return jsonify({"error": "La fecha de fin debe ser posterior a la fecha de inicio"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Calcular días hábiles
        dias_habiles = calcular_dias_habiles(fecha_inicio, fecha_fin, cursor)
        
        # Obtener información adicional de los días
        cursor.execute("""
            SELECT fecha, nombre_dia, categoria
            FROM general_dim_fecha 
            WHERE fecha BETWEEN %s AND %s
            ORDER BY fecha
        """, (fecha_inicio, fecha_fin))
        
        dias_detalle = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "fecha_inicio": data['fecha_inicio'],
            "fecha_fin": data['fecha_fin'],
            "dias_habiles": dias_habiles,
            "dias_detalle": dias_detalle
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint de diagnóstico para verificar datos de fechas
@vacaciones_bp.route('/diagnostico-fechas', methods=['POST'])
@jwt_required()
def diagnostico_fechas():
    try:
        data = request.json
        
        # Validar campos requeridos
        if not data.get('fecha_inicio') or not data.get('fecha_fin'):
            return jsonify({"error": "Faltan campos requeridos: fecha_inicio, fecha_fin"}), 400
        
        # Validar formato de fechas
        try:
            fecha_inicio = datetime.strptime(data['fecha_inicio'], '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(data['fecha_fin'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar categorías disponibles
        cursor.execute("SELECT DISTINCT categoria, COUNT(*) as total FROM general_dim_fecha GROUP BY categoria")
        categorias = cursor.fetchall()
        
        # Verificar datos en el rango específico
        cursor.execute("""
            SELECT fecha, nombre_dia, categoria
            FROM general_dim_fecha 
            WHERE fecha BETWEEN %s AND %s
            ORDER BY fecha
        """, (fecha_inicio, fecha_fin))
        
        dias_rango = cursor.fetchall()
        
        # Contar días hábiles con diferentes criterios
        cursor.execute("""
            SELECT COUNT(*) as total_dias
            FROM general_dim_fecha 
            WHERE fecha BETWEEN %s AND %s
        """, (fecha_inicio, fecha_fin))
        
        total_dias = cursor.fetchone()['total_dias']
        
        cursor.execute("""
            SELECT COUNT(*) as dias_habiles
            FROM general_dim_fecha 
            WHERE fecha BETWEEN %s AND %s AND categoria = 'dia habil'
        """, (fecha_inicio, fecha_fin))
        
        dias_habiles = cursor.fetchone()['dias_habiles']
        
        cursor.execute("""
            SELECT COUNT(*) as dias_no_finde
            FROM general_dim_fecha 
            WHERE fecha BETWEEN %s AND %s 
            AND nombre_dia NOT IN ('Sábado', 'Domingo', 'Saturday', 'Sunday')
        """, (fecha_inicio, fecha_fin))
        
        dias_no_finde = cursor.fetchone()['dias_no_finde']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "fecha_inicio": str(fecha_inicio),
            "fecha_fin": str(fecha_fin),
            "categorias_disponibles": categorias,
            "total_dias_en_rango": total_dias,
            "dias_habiles_por_categoria": dias_habiles,
            "dias_no_finde": dias_no_finde,
            "dias_detalle": dias_rango
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Verificar datos específicos de agosto 2025
@vacaciones_bp.route('/verificar-agosto-2025', methods=['GET'])
@jwt_required()
def verificar_agosto_2025():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar datos del 4 al 14 de agosto de 2025 (como en la imagen)
        fecha_inicio = datetime.strptime('2025-08-04', '%Y-%m-%d').date()
        fecha_fin = datetime.strptime('2025-08-14', '%Y-%m-%d').date()
        
        # Obtener todos los días en ese rango
        cursor.execute("""
            SELECT fecha, nombre_dia, categoria
            FROM general_dim_fecha 
            WHERE fecha BETWEEN %s AND %s
            ORDER BY fecha
        """, (fecha_inicio, fecha_fin))
        
        dias_rango = cursor.fetchall()
        
        # Contar días hábiles
        cursor.execute("""
            SELECT COUNT(*) as dias_habiles
            FROM general_dim_fecha 
            WHERE fecha BETWEEN %s AND %s AND categoria = 'dia habil'
        """, (fecha_inicio, fecha_fin))
        
        dias_habiles = cursor.fetchone()['dias_habiles']
        
        # Calcular días naturales
        from datetime import timedelta
        dias_naturales = 0
        fecha_actual = fecha_inicio
        while fecha_actual <= fecha_fin:
            dias_naturales += 1
            fecha_actual += timedelta(days=1)
        
        # Calcular días hábiles por semana (fallback)
        dias_habiles_fallback = 0
        fecha_actual = fecha_inicio
        while fecha_actual <= fecha_fin:
            if fecha_actual.weekday() < 5:  # Lunes a Viernes
                dias_habiles_fallback += 1
            fecha_actual += timedelta(days=1)
        
        # Verificar si hay datos en la tabla
        cursor.execute("SELECT COUNT(*) as total FROM general_dim_fecha")
        total_registros = cursor.fetchone()['total']
        
        # Verificar rango de fechas disponible
        cursor.execute("SELECT MIN(fecha) as fecha_min, MAX(fecha) as fecha_max FROM general_dim_fecha")
        rango_fechas = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "fecha_inicio_verificada": str(fecha_inicio),
            "fecha_fin_verificada": str(fecha_fin),
            "dias_habiles_encontrados": dias_habiles,
            "dias_habiles_fallback": dias_habiles_fallback,
            "dias_naturales": dias_naturales,
            "total_dias_en_rango": len(dias_rango),
            "dias_detalle": dias_rango,
            "total_registros_tabla": total_registros,
            "rango_fechas_disponible": rango_fechas,
            "usando_fallback": len(dias_rango) == 0
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Verificar estado de la tabla general_dim_fecha
@vacaciones_bp.route('/estado-tabla-fechas', methods=['GET'])
@jwt_required()
def estado_tabla_fechas():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar si la tabla existe y tiene datos
        cursor.execute("SELECT COUNT(*) as total FROM general_dim_fecha")
        total_registros = cursor.fetchone()['total']
        
        # Obtener rango de fechas disponible
        cursor.execute("SELECT MIN(fecha) as fecha_min, MAX(fecha) as fecha_max FROM general_dim_fecha")
        rango_fechas = cursor.fetchone()
        
        # Obtener categorías disponibles
        cursor.execute("SELECT DISTINCT categoria, COUNT(*) as cantidad FROM general_dim_fecha GROUP BY categoria ORDER BY cantidad DESC")
        categorias = cursor.fetchall()
        
        # Verificar datos específicos para agosto 2025
        fecha_inicio_agosto = datetime.strptime('2025-08-01', '%Y-%m-%d').date()
        fecha_fin_agosto = datetime.strptime('2025-08-31', '%Y-%m-%d').date()
        
        cursor.execute("""
            SELECT COUNT(*) as dias_agosto
            FROM general_dim_fecha 
            WHERE fecha BETWEEN %s AND %s
        """, (fecha_inicio_agosto, fecha_fin_agosto))
        
        dias_agosto = cursor.fetchone()['dias_agosto']
        
        # Verificar días hábiles en agosto 2025
        cursor.execute("""
            SELECT COUNT(*) as dias_habiles_agosto
            FROM general_dim_fecha 
            WHERE fecha BETWEEN %s AND %s AND categoria = 'dia habil'
        """, (fecha_inicio_agosto, fecha_fin_agosto))
        
        dias_habiles_agosto = cursor.fetchone()['dias_habiles_agosto']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "total_registros": total_registros,
            "rango_fechas_disponible": rango_fechas,
            "categorias_disponibles": categorias,
            "dias_agosto_2025": dias_agosto,
            "dias_habiles_agosto_2025": dias_habiles_agosto,
            "fecha_inicio_agosto": str(fecha_inicio_agosto),
            "fecha_fin_agosto": str(fecha_fin_agosto)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
