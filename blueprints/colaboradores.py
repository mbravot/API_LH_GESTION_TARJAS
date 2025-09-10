from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
from utils.validar_rut import validar_rut
import uuid

colaboradores_bp = Blueprint('colaboradores_bp', __name__)

# Listar colaboradores (por sucursal activa del usuario)
@colaboradores_bp.route('', methods=['GET'])
@jwt_required()
def listar_colaboradores():
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
        # Listar colaboradores de la sucursal con información relacionada
        cursor.execute("""
            SELECT 
                c.*,
                car.nombre as nombre_cargo,
                a.nombre as nombre_afp,
                p.nombre as nombre_prevision,
                s1.nombre as nombre_sucursal,
                e.nombre as nombre_estado,
                sb.sueldobase,
                sb.base_dia,
                sb.hora_dia,
                sb.fecha as fecha_sueldobase
            FROM general_dim_colaborador c
            LEFT JOIN rrhh_dim_cargo car ON c.id_cargo = car.id
            LEFT JOIN rrhh_dim_afp a ON c.id_afp = a.id
            LEFT JOIN rrhh_dim_prevision p ON c.id_prevision = p.id
            LEFT JOIN general_dim_sucursal s1 ON c.id_sucursal = s1.id
            LEFT JOIN general_dim_estado e ON c.id_estado = e.id
            LEFT JOIN rrhh_fact_sueldobase sb ON c.id_sueldobaseactivo = sb.id
            WHERE c.id_sucursal = %s
            ORDER BY c.nombre, c.apellido_paterno, c.apellido_materno ASC
        """, (id_sucursal,))
        colaboradores = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(colaboradores), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Crear colaborador
@colaboradores_bp.route('/', methods=['POST'])
@jwt_required()
def crear_colaborador():
    try:
        data = request.json
        usuario_id = get_jwt_identity()
        
        # Validaciones de campos obligatorios
        if not data.get('nombre') or not data.get('apellido_paterno'):
            return jsonify({"error": "Nombre y apellido paterno son obligatorios"}), 400
        
        # Validar RUT si viene
        rut = data.get('rut')
        codigo_verificador = data.get('codigo_verificador')
        if rut and codigo_verificador and not validar_rut(str(rut) + codigo_verificador):
            return jsonify({"error": "RUT inválido"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        id_sucursal = usuario['id_sucursalactiva']
        
        # Validar que la sucursal existe
        cursor.execute("SELECT id FROM general_dim_sucursal WHERE id = %s", (id_sucursal,))
        if not cursor.fetchone():
            return jsonify({"error": "Sucursal no válida"}), 400
        
        # Validar cargo si se proporciona
        id_cargo = data.get('id_cargo')
        if id_cargo:
            cursor.execute("SELECT id FROM rrhh_dim_cargo WHERE id = %s", (id_cargo,))
            if not cursor.fetchone():
                return jsonify({"error": "Cargo no válido"}), 400
        
        # Validar previsión si se proporciona
        id_prevision = data.get('id_prevision')
        if id_prevision:
            cursor.execute("SELECT id FROM rrhh_dim_prevision WHERE id = %s", (id_prevision,))
            if not cursor.fetchone():
                return jsonify({"error": "Previsión no válida"}), 400
        
        # Validar AFP si se proporciona
        id_afp = data.get('id_afp')
        if id_afp:
            cursor.execute("SELECT id FROM rrhh_dim_afp WHERE id = %s", (id_afp,))
            if not cursor.fetchone():
                return jsonify({"error": "AFP no válida"}), 400
        
        # Validar estado si se proporciona
        id_estado = data.get('id_estado', 1)
        cursor.execute("SELECT id FROM general_dim_estado WHERE id = %s", (id_estado,))
        if not cursor.fetchone():
            return jsonify({"error": "Estado no válido"}), 400
        
        # Validar sueldo base activo si se proporciona
        id_sueldobaseactivo = data.get('id_sueldobaseactivo')
        if id_sueldobaseactivo:
            cursor.execute("SELECT id FROM rrhh_fact_sueldobase WHERE id = %s", (id_sueldobaseactivo,))
            if not cursor.fetchone():
                return jsonify({"error": "Sueldo base no válido"}), 400
        
        colaborador_id = str(uuid.uuid4())
        sql = """
            INSERT INTO general_dim_colaborador (
                id, nombre, apellido_paterno, apellido_materno, rut, codigo_verificador,
                id_sucursal, id_cargo, fecha_nacimiento, fecha_incorporacion,
                id_prevision, id_afp, id_estado, fecha_finiquito, id_sueldobaseactivo
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            colaborador_id,
            data['nombre'],
            data['apellido_paterno'],
            data.get('apellido_materno'),
            data.get('rut'),
            data.get('codigo_verificador'),
            id_sucursal,
            id_cargo,
            data.get('fecha_nacimiento'),
            data.get('fecha_incorporacion'),
            id_prevision,
            id_afp,
            id_estado,
            data.get('fecha_finiquito'),
            id_sueldobaseactivo
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Colaborador creado correctamente", "id": colaborador_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar colaborador
@colaboradores_bp.route('/<string:colaborador_id>', methods=['PUT'])
@jwt_required()
def editar_colaborador(colaborador_id):
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
        
        # Obtener colaborador actual
        cursor.execute("SELECT * FROM general_dim_colaborador WHERE id = %s AND id_sucursal = %s", (colaborador_id, usuario['id_sucursalactiva']))
        colaborador_actual = cursor.fetchone()
        if not colaborador_actual:
            return jsonify({"error": "Colaborador no encontrado"}), 404
        
        # Validar RUT si se está modificando
        rut = data.get('rut', colaborador_actual['rut'])
        codigo_verificador = data.get('codigo_verificador', colaborador_actual['codigo_verificador'])
        if rut and codigo_verificador and not validar_rut(str(rut) + codigo_verificador):
            return jsonify({"error": "RUT inválido"}), 400
        
        # Conservar valores existentes si no se mandan en el request
        nombre = data.get('nombre', colaborador_actual['nombre'])
        apellido_paterno = data.get('apellido_paterno', colaborador_actual['apellido_paterno'])
        apellido_materno = data.get('apellido_materno', colaborador_actual['apellido_materno'])
        id_cargo = data.get('id_cargo', colaborador_actual['id_cargo'])
        fecha_nacimiento = data.get('fecha_nacimiento', colaborador_actual['fecha_nacimiento'])
        fecha_incorporacion = data.get('fecha_incorporacion', colaborador_actual['fecha_incorporacion'])
        id_prevision = data.get('id_prevision', colaborador_actual['id_prevision'])
        id_afp = data.get('id_afp', colaborador_actual['id_afp'])
        id_estado = data.get('id_estado', colaborador_actual['id_estado'])
        fecha_finiquito = data.get('fecha_finiquito', colaborador_actual['fecha_finiquito'])
        id_sueldobaseactivo = data.get('id_sueldobaseactivo', colaborador_actual['id_sueldobaseactivo'])
        
        # Validar cargo si se está modificando
        if id_cargo and id_cargo != colaborador_actual['id_cargo']:
            cursor.execute("SELECT id FROM rrhh_dim_cargo WHERE id = %s", (id_cargo,))
            if not cursor.fetchone():
                return jsonify({"error": "Cargo no válido"}), 400
        
        # Validar previsión si se está modificando
        if id_prevision and id_prevision != colaborador_actual['id_prevision']:
            cursor.execute("SELECT id FROM rrhh_dim_prevision WHERE id = %s", (id_prevision,))
            if not cursor.fetchone():
                return jsonify({"error": "Previsión no válida"}), 400
        
        # Validar AFP si se está modificando
        if id_afp and id_afp != colaborador_actual['id_afp']:
            cursor.execute("SELECT id FROM rrhh_dim_afp WHERE id = %s", (id_afp,))
            if not cursor.fetchone():
                return jsonify({"error": "AFP no válida"}), 400
        
        # Validar estado si se está modificando
        if id_estado != colaborador_actual['id_estado']:
            cursor.execute("SELECT id FROM general_dim_estado WHERE id = %s", (id_estado,))
            if not cursor.fetchone():
                return jsonify({"error": "Estado no válido"}), 400
        
        # Validar sueldo base activo si se está modificando
        if id_sueldobaseactivo and id_sueldobaseactivo != colaborador_actual['id_sueldobaseactivo']:
            cursor.execute("SELECT id FROM rrhh_fact_sueldobase WHERE id = %s", (id_sueldobaseactivo,))
            if not cursor.fetchone():
                return jsonify({"error": "Sueldo base no válido"}), 400
        
        # Actualizar colaborador
        sql = """
            UPDATE general_dim_colaborador
            SET nombre = %s, apellido_paterno = %s, apellido_materno = %s, rut = %s, codigo_verificador = %s,
                id_cargo = %s, fecha_nacimiento = %s, fecha_incorporacion = %s,
                id_prevision = %s, id_afp = %s, id_estado = %s, fecha_finiquito = %s, id_sueldobaseactivo = %s
            WHERE id = %s
        """
        cursor.execute(sql, (
            nombre,
            apellido_paterno,
            apellido_materno,
            rut,
            codigo_verificador,
            id_cargo,
            fecha_nacimiento,
            fecha_incorporacion,
            id_prevision,
            id_afp,
            id_estado,
            fecha_finiquito,
            id_sueldobaseactivo,
            colaborador_id
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Colaborador actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener colaborador por ID
@colaboradores_bp.route('/<string:colaborador_id>', methods=['GET'])
@jwt_required()
def obtener_colaborador_por_id(colaborador_id):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        cursor.execute("""
            SELECT 
                c.*,
                car.nombre as nombre_cargo,
                a.nombre as nombre_afp,
                p.nombre as nombre_prevision,
                s1.nombre as nombre_sucursal,
                e.nombre as nombre_estado,
                sb.sueldobase,
                sb.base_dia,
                sb.hora_dia,
                sb.fecha as fecha_sueldobase
            FROM general_dim_colaborador c
            LEFT JOIN rrhh_dim_cargo car ON c.id_cargo = car.id
            LEFT JOIN rrhh_dim_afp a ON c.id_afp = a.id
            LEFT JOIN rrhh_dim_prevision p ON c.id_prevision = p.id
            LEFT JOIN general_dim_sucursal s1 ON c.id_sucursal = s1.id
            LEFT JOIN general_dim_estado e ON c.id_estado = e.id
            LEFT JOIN rrhh_fact_sueldobase sb ON c.id_sueldobaseactivo = sb.id
            WHERE c.id = %s AND c.id_sucursal = %s
        """, (colaborador_id, usuario['id_sucursalactiva']))
        
        colaborador = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not colaborador:
            return jsonify({"error": "Colaborador no encontrado"}), 404
            
        return jsonify(colaborador), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener opciones para crear colaborador
@colaboradores_bp.route('/opciones-crear', methods=['GET'])
@jwt_required()
def obtener_opciones_crear_colaborador():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursales
        cursor.execute("SELECT id, nombre FROM general_dim_sucursal ORDER BY nombre")
        sucursales = cursor.fetchall()
        
        # Obtener cargos
        cursor.execute("SELECT id, nombre FROM rrhh_dim_cargo ORDER BY nombre")
        cargos = cursor.fetchall()
        
        # Obtener previsiones
        cursor.execute("SELECT id, nombre FROM rrhh_dim_prevision ORDER BY nombre")
        previsiones = cursor.fetchall()
        
        # Obtener AFPs
        cursor.execute("SELECT id, nombre FROM rrhh_dim_afp ORDER BY nombre")
        afps = cursor.fetchall()
        
        # Obtener estados (sin filtrar por id_tipo_estado)
        cursor.execute("SELECT id, nombre FROM general_dim_estado ORDER BY nombre")
        estados = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'sucursales': sucursales,
            'cargos': cargos,
            'previsiones': previsiones,
            'afps': afps,
            'estados': estados
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener opciones para editar colaborador
@colaboradores_bp.route('/opciones-editar/<string:colaborador_id>', methods=['GET'])
@jwt_required()
def obtener_opciones_editar_colaborador(colaborador_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que el colaborador existe
        cursor.execute("SELECT id FROM general_dim_colaborador WHERE id = %s", (colaborador_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Colaborador no encontrado"}), 404
        
        # Obtener sucursales
        cursor.execute("SELECT id, nombre FROM general_dim_sucursal ORDER BY nombre")
        sucursales = cursor.fetchall()
        
        # Obtener cargos
        cursor.execute("SELECT id, nombre FROM rrhh_dim_cargo ORDER BY nombre")
        cargos = cursor.fetchall()
        
        # Obtener previsiones
        cursor.execute("SELECT id, nombre FROM rrhh_dim_prevision ORDER BY nombre")
        previsiones = cursor.fetchall()
        
        # Obtener AFPs
        cursor.execute("SELECT id, nombre FROM rrhh_dim_afp ORDER BY nombre")
        afps = cursor.fetchall()
        
        # Obtener estados (sin filtrar por id_tipo_estado)
        cursor.execute("SELECT id, nombre FROM general_dim_estado ORDER BY nombre")
        estados = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'sucursales': sucursales,
            'cargos': cargos,
            'previsiones': previsiones,
            'afps': afps,
            'estados': estados
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Eliminar colaborador
@colaboradores_bp.route('/<string:colaborador_id>', methods=['DELETE'])
@jwt_required()
def eliminar_colaborador(colaborador_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que el colaborador existe
        cursor.execute("SELECT id, nombre, apellido_paterno, apellido_materno, id_sucursal FROM general_dim_colaborador WHERE id = %s", (colaborador_id,))
        colaborador = cursor.fetchone()
        
        if not colaborador:
            return jsonify({"error": "Colaborador no encontrado"}), 404
        
        # Verificar que el usuario tiene permisos para eliminar colaboradores de la sucursal
        usuario_id = get_jwt_identity()
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        # Verificar que el colaborador pertenece a la sucursal activa del usuario
        if colaborador['id_sucursal'] != usuario['id_sucursalactiva']:
            return jsonify({"error": "No tienes permisos para eliminar este colaborador"}), 403
        
        # Eliminar el colaborador
        cursor.execute("DELETE FROM general_dim_colaborador WHERE id = %s", (colaborador_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        nombre_completo = f"{colaborador['nombre']} {colaborador['apellido_paterno']} {colaborador.get('apellido_materno', '')}".strip()
        
        return jsonify({
            "message": f"Colaborador '{nombre_completo}' eliminado correctamente",
            "colaborador_eliminado": {
                "id": colaborador_id,
                "nombre_completo": nombre_completo
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== ENDPOINTS PARA GESTIONAR SUELDOS BASE ====================

# Listar sueldos base de un colaborador
@colaboradores_bp.route('/<string:colaborador_id>/sueldos-base', methods=['GET'])
@jwt_required()
def listar_sueldos_base_colaborador(colaborador_id):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        # Verificar que el colaborador existe y pertenece a la sucursal del usuario
        cursor.execute("""
            SELECT id FROM general_dim_colaborador 
            WHERE id = %s AND id_sucursal = %s
        """, (colaborador_id, usuario['id_sucursalactiva']))
        if not cursor.fetchone():
            return jsonify({"error": "Colaborador no encontrado"}), 404
        
        # Listar sueldos base del colaborador ordenados por fecha descendente
        cursor.execute("""
            SELECT 
                sb.*,
                c.nombre, c.apellido_paterno, c.apellido_materno
            FROM rrhh_fact_sueldobase sb
            JOIN general_dim_colaborador c ON sb.id_colaborador = c.id
            WHERE sb.id_colaborador = %s
            ORDER BY sb.fecha DESC, sb.id DESC
        """, (colaborador_id,))
        
        sueldos_base = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(sueldos_base), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Crear nuevo sueldo base para un colaborador
@colaboradores_bp.route('/<string:colaborador_id>/sueldos-base', methods=['POST'])
@jwt_required()
def crear_sueldo_base_colaborador(colaborador_id):
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
        
        # Verificar que el colaborador existe y pertenece a la sucursal del usuario
        cursor.execute("""
            SELECT id FROM general_dim_colaborador 
            WHERE id = %s AND id_sucursal = %s
        """, (colaborador_id, usuario['id_sucursalactiva']))
        if not cursor.fetchone():
            return jsonify({"error": "Colaborador no encontrado"}), 404
        
        # Validar campos requeridos
        if not data.get('sueldobase') or not data.get('fecha'):
            return jsonify({"error": "Los campos sueldobase y fecha son requeridos"}), 400
        
        sueldobase = data.get('sueldobase')
        fecha = data.get('fecha')
        
        # Validar que sueldobase sea un número positivo
        try:
            sueldobase = int(sueldobase)
            if sueldobase <= 0:
                return jsonify({"error": "El sueldo base debe ser un número positivo"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "El sueldo base debe ser un número válido"}), 400
        
        # Insertar nuevo sueldo base
        sql = """
            INSERT INTO rrhh_fact_sueldobase (sueldobase, id_colaborador, fecha)
            VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (sueldobase, colaborador_id, fecha))
        conn.commit()
        
        # Obtener el ID del sueldo base creado
        sueldo_base_id = cursor.lastrowid
        
        # Obtener los datos completos del sueldo base creado
        cursor.execute("""
            SELECT 
                sb.*,
                c.nombre, c.apellido_paterno, c.apellido_materno
            FROM rrhh_fact_sueldobase sb
            JOIN general_dim_colaborador c ON sb.id_colaborador = c.id
            WHERE sb.id = %s
        """, (sueldo_base_id,))
        
        sueldo_base_creado = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Sueldo base creado correctamente",
            "sueldo_base": sueldo_base_creado
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar sueldo base
@colaboradores_bp.route('/sueldos-base/<int:sueldo_base_id>', methods=['PUT'])
@jwt_required()
def editar_sueldo_base(sueldo_base_id):
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
        
        # Verificar que el sueldo base existe y el colaborador pertenece a la sucursal del usuario
        cursor.execute("""
            SELECT sb.*, c.id_sucursal
            FROM rrhh_fact_sueldobase sb
            JOIN general_dim_colaborador c ON sb.id_colaborador = c.id
            WHERE sb.id = %s AND c.id_sucursal = %s
        """, (sueldo_base_id, usuario['id_sucursalactiva']))
        
        sueldo_base_actual = cursor.fetchone()
        if not sueldo_base_actual:
            return jsonify({"error": "Sueldo base no encontrado"}), 404
        
        # Validar campos si se proporcionan
        sueldobase = data.get('sueldobase', sueldo_base_actual['sueldobase'])
        fecha = data.get('fecha', sueldo_base_actual['fecha'])
        
        # Validar que sueldobase sea un número positivo si se está modificando
        if 'sueldobase' in data:
            try:
                sueldobase = int(sueldobase)
                if sueldobase <= 0:
                    return jsonify({"error": "El sueldo base debe ser un número positivo"}), 400
            except (ValueError, TypeError):
                return jsonify({"error": "El sueldo base debe ser un número válido"}), 400
        
        # Actualizar sueldo base
        sql = """
            UPDATE rrhh_fact_sueldobase
            SET sueldobase = %s, fecha = %s
            WHERE id = %s
        """
        cursor.execute(sql, (sueldobase, fecha, sueldo_base_id))
        conn.commit()
        
        # Obtener los datos actualizados del sueldo base
        cursor.execute("""
            SELECT 
                sb.*,
                c.nombre, c.apellido_paterno, c.apellido_materno
            FROM rrhh_fact_sueldobase sb
            JOIN general_dim_colaborador c ON sb.id_colaborador = c.id
            WHERE sb.id = %s
        """, (sueldo_base_id,))
        
        sueldo_base_actualizado = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Sueldo base actualizado correctamente",
            "sueldo_base": sueldo_base_actualizado
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Eliminar sueldo base
@colaboradores_bp.route('/sueldos-base/<int:sueldo_base_id>', methods=['DELETE'])
@jwt_required()
def eliminar_sueldo_base(sueldo_base_id):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        # Verificar que el sueldo base existe y el colaborador pertenece a la sucursal del usuario
        cursor.execute("""
            SELECT sb.*, c.nombre, c.apellido_paterno, c.apellido_materno, c.id_sucursal
            FROM rrhh_fact_sueldobase sb
            JOIN general_dim_colaborador c ON sb.id_colaborador = c.id
            WHERE sb.id = %s AND c.id_sucursal = %s
        """, (sueldo_base_id, usuario['id_sucursalactiva']))
        
        sueldo_base = cursor.fetchone()
        if not sueldo_base:
            return jsonify({"error": "Sueldo base no encontrado"}), 404
        
        # Eliminar el sueldo base
        cursor.execute("DELETE FROM rrhh_fact_sueldobase WHERE id = %s", (sueldo_base_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        nombre_colaborador = f"{sueldo_base['nombre']} {sueldo_base['apellido_paterno']} {sueldo_base.get('apellido_materno', '')}".strip()
        
        return jsonify({
            "message": f"Sueldo base de {nombre_colaborador} eliminado correctamente",
            "sueldo_base_eliminado": {
                "id": sueldo_base_id,
                "sueldobase": sueldo_base['sueldobase'],
                "fecha": sueldo_base['fecha'],
                "colaborador": nombre_colaborador
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
