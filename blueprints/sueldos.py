from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
from datetime import datetime

sueldos_bp = Blueprint('sueldos', __name__)

@sueldos_bp.route('/sueldos-base', methods=['GET'])
@jwt_required()
def listar_sueldos_base():
    """Listar todos los sueldos base con información del colaborador"""
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
        
        # Listar sueldos base con información del colaborador
        cursor.execute("""
            SELECT 
                sb.id,
                sb.sueldobase,
                sb.id_colaborador,
                sb.fecha,
                sb.base_dia,
                sb.hora_dia,
                CONCAT(c.nombre, ' ', c.apellido_paterno,
                       CASE WHEN c.apellido_materno IS NOT NULL 
                            THEN CONCAT(' ', c.apellido_materno) 
                            ELSE '' END) as nombre_colaborador,
                c.rut,
                s.nombre as nombre_sucursal
            FROM rrhh_fact_sueldobase sb
            INNER JOIN general_dim_colaborador c ON sb.id_colaborador = c.id
            INNER JOIN general_dim_sucursal s ON c.id_sucursal = s.id
            WHERE c.id_sucursal = %s
            ORDER BY sb.fecha DESC, c.nombre, c.apellido_paterno
        """, (id_sucursal,))
        
        sueldos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(sueldos), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sueldos_bp.route('/sueldos-base/<int:sueldo_id>', methods=['GET'])
@jwt_required()
def obtener_sueldo_base(sueldo_id):
    """Obtener un sueldo base específico por ID"""
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
        
        # Obtener sueldo base específico
        cursor.execute("""
            SELECT 
                sb.id,
                sb.sueldobase,
                sb.id_colaborador,
                sb.fecha,
                sb.base_dia,
                sb.hora_dia,
                CONCAT(c.nombre, ' ', c.apellido_paterno,
                       CASE WHEN c.apellido_materno IS NOT NULL 
                            THEN CONCAT(' ', c.apellido_materno) 
                            ELSE '' END) as nombre_colaborador,
                c.rut,
                s.nombre as nombre_sucursal
            FROM rrhh_fact_sueldobase sb
            INNER JOIN general_dim_colaborador c ON sb.id_colaborador = c.id
            INNER JOIN general_dim_sucursal s ON c.id_sucursal = s.id
            WHERE sb.id = %s AND c.id_sucursal = %s
        """, (sueldo_id, id_sucursal))
        
        sueldo = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not sueldo:
            return jsonify({"error": "Sueldo base no encontrado"}), 404
            
        return jsonify(sueldo), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sueldos_bp.route('/sueldos-base', methods=['POST'])
@jwt_required()
def crear_sueldo_base():
    """Crear un nuevo sueldo base"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not data:
            return jsonify({"error": "No se proporcionaron datos"}), 400
            
        sueldobase = data.get('sueldobase')
        id_colaborador = data.get('id_colaborador')
        fecha = data.get('fecha')
        
        if not sueldobase or not id_colaborador or not fecha:
            return jsonify({
                "error": "Faltan campos requeridos: sueldobase, id_colaborador, fecha"
            }), 400
            
        # Validar que el sueldo base sea un número positivo
        try:
            sueldobase = int(sueldobase)
            if sueldobase <= 0:
                return jsonify({"error": "El sueldo base debe ser un número positivo"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "El sueldo base debe ser un número válido"}), 400
            
        # Validar formato de fecha
        try:
            datetime.strptime(fecha, '%Y-%m-%d')
        except ValueError:
            return jsonify({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}), 400
            
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
        
        # Verificar que el colaborador existe y pertenece a la sucursal del usuario
        cursor.execute("""
            SELECT id FROM general_dim_colaborador 
            WHERE id = %s AND id_sucursal = %s
        """, (id_colaborador, id_sucursal))
        
        colaborador = cursor.fetchone()
        if not colaborador:
            return jsonify({"error": "Colaborador no encontrado o no pertenece a su sucursal"}), 404
            
        # Crear el sueldo base
        cursor.execute("""
            INSERT INTO rrhh_fact_sueldobase (sueldobase, id_colaborador, fecha)
            VALUES (%s, %s, %s)
        """, (sueldobase, id_colaborador, fecha))
        
        sueldo_id = cursor.lastrowid
        conn.commit()
        
        # Obtener el sueldo base creado con información del colaborador
        cursor.execute("""
            SELECT 
                sb.id,
                sb.sueldobase,
                sb.id_colaborador,
                sb.fecha,
                sb.base_dia,
                sb.hora_dia,
                CONCAT(c.nombre, ' ', c.apellido_paterno,
                       CASE WHEN c.apellido_materno IS NOT NULL 
                            THEN CONCAT(' ', c.apellido_materno) 
                            ELSE '' END) as nombre_colaborador,
                c.rut,
                s.nombre as nombre_sucursal
            FROM rrhh_fact_sueldobase sb
            INNER JOIN general_dim_colaborador c ON sb.id_colaborador = c.id
            INNER JOIN general_dim_sucursal s ON c.id_sucursal = s.id
            WHERE sb.id = %s
        """, (sueldo_id,))
        
        sueldo_creado = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Sueldo base creado correctamente",
            "sueldo": sueldo_creado
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sueldos_bp.route('/sueldos-base/<int:sueldo_id>', methods=['PUT'])
@jwt_required()
def editar_sueldo_base(sueldo_id):
    """Editar un sueldo base existente"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No se proporcionaron datos"}), 400
            
        sueldobase = data.get('sueldobase')
        id_colaborador = data.get('id_colaborador')
        fecha = data.get('fecha')
        
        # Validar que al menos un campo sea proporcionado
        if not any([sueldobase, id_colaborador, fecha]):
            return jsonify({"error": "Debe proporcionar al menos un campo para actualizar"}), 400
            
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
        
        # Verificar que el sueldo base existe y pertenece a un colaborador de la sucursal
        cursor.execute("""
            SELECT sb.id FROM rrhh_fact_sueldobase sb
            INNER JOIN general_dim_colaborador c ON sb.id_colaborador = c.id
            WHERE sb.id = %s AND c.id_sucursal = %s
        """, (sueldo_id, id_sucursal))
        
        sueldo_existente = cursor.fetchone()
        if not sueldo_existente:
            return jsonify({"error": "Sueldo base no encontrado o no pertenece a su sucursal"}), 404
            
        # Validar sueldo base si se proporciona
        if sueldobase is not None:
            try:
                sueldobase = int(sueldobase)
                if sueldobase <= 0:
                    return jsonify({"error": "El sueldo base debe ser un número positivo"}), 400
            except (ValueError, TypeError):
                return jsonify({"error": "El sueldo base debe ser un número válido"}), 400
                
        # Validar colaborador si se proporciona
        if id_colaborador:
            cursor.execute("""
                SELECT id FROM general_dim_colaborador 
                WHERE id = %s AND id_sucursal = %s
            """, (id_colaborador, id_sucursal))
            
            colaborador = cursor.fetchone()
            if not colaborador:
                return jsonify({"error": "Colaborador no encontrado o no pertenece a su sucursal"}), 404
                
        # Validar fecha si se proporciona
        if fecha:
            try:
                datetime.strptime(fecha, '%Y-%m-%d')
            except ValueError:
                return jsonify({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}), 400
                
        # Construir query de actualización dinámicamente
        campos_actualizar = []
        valores = []
        
        if sueldobase is not None:
            campos_actualizar.append("sueldobase = %s")
            valores.append(sueldobase)
            
        if id_colaborador:
            campos_actualizar.append("id_colaborador = %s")
            valores.append(id_colaborador)
            
        if fecha:
            campos_actualizar.append("fecha = %s")
            valores.append(fecha)
            
        valores.append(sueldo_id)
        
        query = f"""
            UPDATE rrhh_fact_sueldobase 
            SET {', '.join(campos_actualizar)}
            WHERE id = %s
        """
        
        cursor.execute(query, valores)
        conn.commit()
        
        # Obtener el sueldo base actualizado
        cursor.execute("""
            SELECT 
                sb.id,
                sb.sueldobase,
                sb.id_colaborador,
                sb.fecha,
                sb.base_dia,
                sb.hora_dia,
                CONCAT(c.nombre, ' ', c.apellido_paterno,
                       CASE WHEN c.apellido_materno IS NOT NULL 
                            THEN CONCAT(' ', c.apellido_materno) 
                            ELSE '' END) as nombre_colaborador,
                c.rut,
                s.nombre as nombre_sucursal
            FROM rrhh_fact_sueldobase sb
            INNER JOIN general_dim_colaborador c ON sb.id_colaborador = c.id
            INNER JOIN general_dim_sucursal s ON c.id_sucursal = s.id
            WHERE sb.id = %s
        """, (sueldo_id,))
        
        sueldo_actualizado = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Sueldo base actualizado correctamente",
            "sueldo": sueldo_actualizado
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sueldos_bp.route('/sueldos-base/<int:sueldo_id>', methods=['DELETE'])
@jwt_required()
def eliminar_sueldo_base(sueldo_id):
    """Eliminar un sueldo base"""
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
        
        # Verificar que el sueldo base existe y pertenece a un colaborador de la sucursal
        cursor.execute("""
            SELECT sb.id FROM rrhh_fact_sueldobase sb
            INNER JOIN general_dim_colaborador c ON sb.id_colaborador = c.id
            WHERE sb.id = %s AND c.id_sucursal = %s
        """, (sueldo_id, id_sucursal))
        
        sueldo_existente = cursor.fetchone()
        if not sueldo_existente:
            return jsonify({"error": "Sueldo base no encontrado o no pertenece a su sucursal"}), 404
            
        # Eliminar el sueldo base
        cursor.execute("DELETE FROM rrhh_fact_sueldobase WHERE id = %s", (sueldo_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Sueldo base eliminado correctamente"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sueldos_bp.route('/colaboradores/<colaborador_id>/sueldos-base', methods=['GET'])
@jwt_required()
def listar_sueldos_base_colaborador(colaborador_id):
    """Listar todos los sueldos base de un colaborador específico"""
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
        
        # Verificar que el colaborador existe y pertenece a la sucursal
        cursor.execute("""
            SELECT id, CONCAT(nombre, ' ', apellido_paterno,
                   CASE WHEN apellido_materno IS NOT NULL 
                        THEN CONCAT(' ', apellido_materno) 
                        ELSE '' END) as nombre_completo
            FROM general_dim_colaborador 
            WHERE id = %s AND id_sucursal = %s
        """, (colaborador_id, id_sucursal))
        
        colaborador = cursor.fetchone()
        if not colaborador:
            return jsonify({"error": "Colaborador no encontrado o no pertenece a su sucursal"}), 404
            
        # Listar sueldos base del colaborador
        cursor.execute("""
            SELECT 
                sb.id,
                sb.sueldobase,
                sb.id_colaborador,
                sb.fecha,
                sb.base_dia,
                sb.hora_dia
            FROM rrhh_fact_sueldobase sb
            WHERE sb.id_colaborador = %s
            ORDER BY sb.fecha DESC
        """, (colaborador_id,))
        
        sueldos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            "colaborador": {
                "id": colaborador['id'],
                "nombre_completo": colaborador['nombre_completo']
            },
            "sueldos_base": sueldos
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
