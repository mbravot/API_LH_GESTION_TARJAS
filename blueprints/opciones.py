from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
#from blueprints.auth import token_requerido
import uuid

opciones_bp = Blueprint('opciones_bp', __name__)

# Endpoint raíz para el blueprint
@opciones_bp.route('/', methods=['GET', 'OPTIONS'])
@jwt_required()
def opciones_root():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, nombre FROM general_dim_labor ORDER BY nombre ASC")
        labores = cursor.fetchall() or []

        cursor.execute("SELECT id, nombre FROM tarja_dim_unidad WHERE id_estado = 1 ORDER BY nombre ASC")
        unidades = cursor.fetchall() or []

        cursor.execute("SELECT id, nombre FROM general_dim_cecotipo ORDER BY nombre ASC")
        tipoCecos = cursor.fetchall() or []

        cursor.close()
        conn.close()

        return jsonify({
            "labores": labores,
            "unidades": unidades,
            "tipoCecos": tipoCecos
        }), 200
    except Exception as e:
        return jsonify({
            "labores": [],
            "unidades": [],
            "tipoCecos": [],
            "error": str(e)
        }), 500

# Obtener especies
@opciones_bp.route('/especies', methods=['GET', 'OPTIONS'])
@jwt_required()
def obtener_especies():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔹 Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400

        # Obtener todas las especies
        cursor.execute("""
            SELECT id, nombre, caja_equivalente
            FROM general_dim_especie 
            ORDER BY nombre ASC
        """)

        especies = cursor.fetchall()
        cursor.close()
        conn.close()

        if not especies:
            return jsonify([]), 200

        return jsonify(especies), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener variedades filtradas por especie
@opciones_bp.route('/variedades', methods=['GET'])
@jwt_required()
def obtener_variedades_filtradas():
    try:
        id_especie = request.args.get('id_especie')
        if not id_especie:
            return jsonify({"error": "id_especie es requerido"}), 400
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nombre
            FROM general_dim_variedad
            WHERE id_especie = %s
            ORDER BY nombre ASC
        """, (id_especie,))
        variedades = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(variedades), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    # Obtener cecos
@opciones_bp.route('/cecos', methods=['GET', 'OPTIONS'])
@jwt_required()
def obtener_cecos():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔹 Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400

        id_sucursal = usuario['id_sucursalactiva']

        # Obtener CECOs según sucursal activa
        cursor.execute("""
            SELECT c.id, c.nombre, c.id_cecotipo, t.nombre as nombre_tipo
            FROM general_dim_ceco c
            LEFT JOIN general_dim_cecotipo t ON c.id_cecotipo = t.id
            WHERE c.id_sucursal = %s
            ORDER BY c.nombre ASC
        """, (id_sucursal,))

        cecos = cursor.fetchall()
        cursor.close()
        conn.close()

        if not cecos:
            return jsonify([]), 200

        return jsonify(cecos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

     # Obtener tipo trabajador
@opciones_bp.route('/tipotrabajadores', methods=['GET'])
@jwt_required()
def obtener_tipotrabajador():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener tipos de trabajador
        cursor.execute("""
            SELECT id, nombre 
            FROM general_dim_tipotrabajador 
            ORDER BY nombre ASC
        """)
        
        tipotrabajador = cursor.fetchall()
        cursor.close()
        conn.close()

        if not tipotrabajador:
            return jsonify([]), 200

        return jsonify(tipotrabajador), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Obtener contratistas según la sucursal activa del usuario logueado
@opciones_bp.route('/contratistas', methods=['GET'])
@jwt_required()
def obtener_contratistas():
    try:
        usuario_id = get_jwt_identity()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔹 Obtener sucursal_activa del usuario autenticado
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400

        id_sucursal = usuario['id_sucursalactiva']

        # 🔹 Obtener contratistas de la sucursal activa
        cursor.execute("""
            SELECT DISTINCT c.id, c.nombre, c.rut, c.codigo_verificador
            FROM general_dim_contratista c
            JOIN general_pivot_contratista_sucursal p ON c.id = p.id_contratista
            WHERE p.id_sucursal = %s AND c.id_estado = 1
            ORDER BY c.nombre ASC
        """, (id_sucursal,))

        contratistas = cursor.fetchall()

        cursor.close()
        conn.close()

        if not contratistas:
            return jsonify([]), 200

        return jsonify(contratistas), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    # Obtener tipo rendimiento
@opciones_bp.route('/tiporendimientos', methods=['GET'])
@jwt_required()
def obtener_tiporendimiento():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener tipos de rendimiento
        cursor.execute("""
            SELECT id, nombre 
            FROM tarja_dim_tiporendimiento 
            ORDER BY nombre ASC
        """)
        
        tiporendimiento = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not tiporendimiento:
            return jsonify([]), 200
            
        return jsonify(tiporendimiento), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Obtener porcentajes de trabajadores
@opciones_bp.route('/porcentajes', methods=['GET'])
@jwt_required()
def obtener_porcentajes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, porcentaje FROM Porcentaje_trabajador ORDER BY porcentaje ASC")
        porcentajes = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(porcentajes), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener CECOs administrativos de la sucursal activa del usuario logueado
@opciones_bp.route('/cecos/administrativos', methods=['GET'])
@jwt_required()
def obtener_cecos_administrativos():
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

        # Obtener los CECOs administrativos de la sucursal activa
        cursor.execute("""
            SELECT id, nombre
            FROM general_dim_ceco
            WHERE id_cecotipo = 1 AND id_sucursal = %s
            ORDER BY nombre ASC
        """, (id_sucursal,))

        cecos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not cecos:
            return jsonify([]), 200
            
        return jsonify(cecos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Crear ceco administrativo
@opciones_bp.route('/cecosadministrativos', methods=['POST'])
@jwt_required()
def crear_cecoadministrativo():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insertar ceco administrativo (sin el campo id)
        cursor.execute("""
            INSERT INTO tarja_fact_cecoadministrativo (
                id_actividad, id_ceco
            ) VALUES (%s, %s)
        """, (
            data['id_actividad'],
            data['id_ceco']
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Ceco administrativo creado correctamente"
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Eliminar CECO administrativo
@opciones_bp.route('/cecosadministrativos/<string:id>', methods=['DELETE'])
@jwt_required()
def eliminar_cecoadministrativo(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Eliminar CECO administrativo
        cursor.execute("DELETE FROM tarja_fact_cecoadministrativo WHERE id = %s", (id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Ceco administrativo no encontrado"}), 404
            
        cursor.close()
        conn.close()
        
        return jsonify({"message": "Ceco administrativo eliminado correctamente"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener CECOs de inversión por actividad
@opciones_bp.route('/cecosinversion/<string:id_actividad>', methods=['GET'])
@jwt_required()
def obtener_cecosinversion(id_actividad):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener CECOs de inversión de la actividad
        cursor.execute("""
            SELECT ci.id, ci.id_actividad, ci.id_tipoinversion, ci.id_inversion, ci.id_ceco,
                   c.nombre as nombre_ceco, ti.nombre as nombre_tipo, i.nombre as nombre_inversion
            FROM tarja_fact_cecoinversion ci
            JOIN general_dim_ceco c ON ci.id_ceco = c.id
            JOIN general_dim_tipoinversion ti ON ci.id_tipoinversion = ti.id
            JOIN general_dim_inversion i ON ci.id_inversion = i.id
            WHERE ci.id_actividad = %s
            ORDER BY c.nombre ASC
        """, (id_actividad,))
        
        cecos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not cecos:
            return jsonify([]), 200
            
        return jsonify(cecos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Crear ceco inversión
@opciones_bp.route('/cecosinversion', methods=['POST'])
@jwt_required()
def crear_cecoinversion():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insertar ceco inversión (sin el campo id)
        cursor.execute("""
            INSERT INTO tarja_fact_cecoinversion (
                id_actividad, id_tipoinversion, 
                id_inversion, id_ceco
            ) VALUES (%s, %s, %s, %s)
        """, (
            data['id_actividad'],
            data['id_tipoinversion'],
            data['id_inversion'],
            data['id_ceco']
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Ceco inversión creado correctamente"
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Eliminar CECO de inversión
@opciones_bp.route('/cecosinversion/<string:id>', methods=['DELETE'])
@jwt_required()
def eliminar_cecoinversion(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Eliminar CECO de inversión
        cursor.execute("DELETE FROM tarja_fact_cecoinversion WHERE id = %s", (id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Ceco inversión no encontrado"}), 404

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Ceco inversión eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener CECOs de maquinaria por actividad
@opciones_bp.route('/cecosmaquinaria/<string:id_actividad>', methods=['GET'])
@jwt_required()
def obtener_cecosmaquinaria(id_actividad):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener CECOs de maquinaria de la actividad
        cursor.execute("""
            SELECT cm.id, cm.id_actividad, cm.id_tipomaquinaria, cm.id_maquinaria, cm.id_ceco,
                   c.nombre as nombre_ceco, tm.nombre as nombre_tipo, m.nombre as nombre_maquinaria
            FROM tarja_fact_cecomaquinaria cm
            JOIN general_dim_ceco c ON cm.id_ceco = c.id
            JOIN general_dim_maquinariatipo tm ON cm.id_tipomaquinaria = tm.id
            JOIN general_dim_maquinaria m ON cm.id_maquinaria = m.id
            WHERE cm.id_actividad = %s
            ORDER BY c.nombre ASC
        """, (id_actividad,))
        
        cecos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not cecos:
            return jsonify([]), 200
            
        return jsonify(cecos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Crear ceco maquinaria
@opciones_bp.route('/cecosmaquinaria', methods=['POST'])
@jwt_required()
def crear_cecomaquinaria():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insertar ceco maquinaria (sin el campo id)
        cursor.execute("""
            INSERT INTO tarja_fact_cecomaquinaria (
                id_actividad, id_tipomaquinaria, 
                id_maquinaria, id_ceco
            ) VALUES (%s, %s, %s, %s)
        """, (
            data['id_actividad'],
            data['id_tipomaquinaria'],
            data['id_maquinaria'],
            data['id_ceco']
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Ceco maquinaria creado correctamente"
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Eliminar CECO de maquinaria
@opciones_bp.route('/cecosmaquinaria/<string:id>', methods=['DELETE'])
@jwt_required()
def eliminar_cecomaquinaria(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Eliminar CECO de maquinaria
        cursor.execute("DELETE FROM tarja_fact_cecomaquinaria WHERE id = %s", (id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Ceco maquinaria no encontrado"}), 404

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Ceco maquinaria eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener CECOs productivos por actividad
@opciones_bp.route('/cecosproductivos/<string:id_actividad>', methods=['GET'])
@jwt_required()
def obtener_cecosproductivos(id_actividad):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener CECOs productivos de la actividad
        cursor.execute("""
            SELECT cp.id, cp.id_actividad, cp.id_especie, cp.id_variedad, cp.id_cuartel, cp.id_ceco,
                   c.nombre as nombre_ceco, e.nombre as nombre_especie, v.nombre as nombre_variedad,
                   cu.nombre as nombre_cuartel
            FROM tarja_fact_cecoproductivo cp
            JOIN general_dim_ceco c ON cp.id_ceco = c.id
            JOIN general_dim_especie e ON cp.id_especie = e.id
            JOIN general_dim_variedad v ON cp.id_variedad = v.id
            JOIN general_dim_cuartel cu ON cp.id_cuartel = cu.id
            WHERE cp.id_actividad = %s
            ORDER BY c.nombre ASC
        """, (id_actividad,))
        
        cecos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not cecos:
            return jsonify([]), 200
            
        return jsonify(cecos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Crear ceco productivo
@opciones_bp.route('/cecosproductivos', methods=['POST'])
@jwt_required()
def crear_cecoproductivo():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insertar ceco productivo (sin el campo id)
        cursor.execute("""
            INSERT INTO tarja_fact_cecoproductivo (
                id_actividad, id_especie, id_variedad, 
                id_cuartel, id_ceco
            ) VALUES (%s, %s, %s, %s, %s)
        """, (
            data['id_actividad'],
            data['id_especie'],
            data['id_variedad'],
            data['id_cuartel'],
            data['id_ceco']
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Ceco productivo creado correctamente"
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Eliminar CECO productivo
@opciones_bp.route('/cecosproductivos/<string:id>', methods=['DELETE'])
@jwt_required()
def eliminar_cecoproductivo(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Eliminar CECO productivo
        cursor.execute("DELETE FROM tarja_fact_cecoproductivo WHERE id = %s", (id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Ceco productivo no encontrado"}), 404

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Ceco productivo eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener CECOs de riego por actividad
@opciones_bp.route('/cecosriego/<string:id_actividad>', methods=['GET'])
@jwt_required()
def obtener_cecosriego(id_actividad):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener CECOs de riego de la actividad
        cursor.execute("""
            SELECT cr.id, cr.id_actividad, cr.id_caseta, cr.id_equiporiego, cr.id_sectorriego, cr.id_ceco,
                   c.nombre as nombre_ceco, ca.nombre as nombre_caseta, 
                   e.nombre as nombre_equipo, s.nombre as nombre_sector
            FROM tarja_fact_cecoriego cr
            JOIN general_dim_ceco c ON cr.id_ceco = c.id
            JOIN riego_dim_caseta ca ON cr.id_caseta = ca.id
            JOIN riego_dim_equipo e ON cr.id_equiporiego = e.id
            JOIN riego_dim_sector s ON cr.id_sectorriego = s.id
            WHERE cr.id_actividad = %s
            ORDER BY c.nombre ASC
        """, (id_actividad,))
        
        cecos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not cecos:
            return jsonify([]), 200
            
        return jsonify(cecos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Crear ceco riego
@opciones_bp.route('/cecosriego', methods=['POST'])
@jwt_required()
def crear_cecoriego():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insertar ceco riego (sin el campo id)
        cursor.execute("""
            INSERT INTO tarja_fact_cecoriego (
                id_actividad, id_caseta, id_equiporiego,
                id_sectorriego, id_ceco
            ) VALUES (%s, %s, %s, %s, %s)
        """, (
            data['id_actividad'],
            data['id_caseta'],
            data['id_equiporiego'],
            data['id_sectorriego'],
            data['id_ceco']
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Ceco riego creado correctamente"
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Eliminar CECO de riego
@opciones_bp.route('/cecosriego/<string:id>', methods=['DELETE'])
@jwt_required()
def eliminar_cecoriego(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Eliminar CECO de riego
        cursor.execute("DELETE FROM tarja_fact_cecoriego WHERE id = %s", (id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Ceco riego no encontrado"}), 404

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Ceco riego eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint de prueba
@opciones_bp.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "Blueprint de opciones funcionando correctamente"}), 200

# Obtener tipos de CECO
@opciones_bp.route('/tiposceco', methods=['GET', 'OPTIONS'])
@jwt_required()
def obtener_tiposceco():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre FROM general_dim_cecotipo ORDER BY nombre ASC")
        tipos = cursor.fetchall()
        cursor.close()
        conn.close()
        if not tipos:
            return jsonify([]), 200
        return jsonify(tipos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Listar todas las rutas registradas
@opciones_bp.route('/rutas', methods=['GET'])
def listar_rutas():
    rutas = []
    for rule in opciones_bp.url_map.iter_rules():
        rutas.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'route': str(rule)
        })
    return jsonify(rutas), 200

# Obtener CECOs productivos de la sucursal activa del usuario logueado
@opciones_bp.route('/cecos/productivos', methods=['GET'])
@jwt_required()
def obtener_cecos_productivos():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        id_sucursal = usuario['id_sucursalactiva']
        cursor.execute("""
            SELECT id, nombre
            FROM general_dim_ceco
            WHERE id_cecotipo = 2 AND id_sucursal = %s
            ORDER BY nombre ASC
        """, (id_sucursal,))
        cecos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(cecos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener CECOs de maquinaria de la sucursal activa del usuario logueado
@opciones_bp.route('/cecos/maquinaria', methods=['GET'])
@jwt_required()
def obtener_cecos_maquinaria():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        id_sucursal = usuario['id_sucursalactiva']
        cursor.execute("""
            SELECT id, nombre
            FROM general_dim_ceco
            WHERE id_cecotipo = 3 AND id_sucursal = %s
            ORDER BY nombre ASC
        """, (id_sucursal,))
        cecos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(cecos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener CECOs de inversión de la sucursal activa del usuario logueado
@opciones_bp.route('/cecos/inversion', methods=['GET'])
@jwt_required()
def obtener_cecos_inversion():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        id_sucursal = usuario['id_sucursalactiva']
        cursor.execute("""
            SELECT id, nombre
            FROM general_dim_ceco
            WHERE id_cecotipo = 4 AND id_sucursal = %s
            ORDER BY nombre ASC
        """, (id_sucursal,))
        cecos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(cecos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener CECOs de riego de la sucursal activa del usuario logueado
@opciones_bp.route('/cecos/riego', methods=['GET'])
@jwt_required()
def obtener_cecos_riego():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        id_sucursal = usuario['id_sucursalactiva']
        cursor.execute("""
            SELECT id, nombre
            FROM general_dim_ceco
            WHERE id_cecotipo = 5 AND id_sucursal = %s
            ORDER BY nombre ASC
        """, (id_sucursal,))
        cecos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(cecos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener cuarteles filtrados por variedad y sucursal de la actividad
@opciones_bp.route('/cuarteles/actividad/<string:id_actividad>', methods=['GET'])
@jwt_required()
def obtener_cuarteles_por_actividad(id_actividad):
    try:
        id_variedad = request.args.get('id_variedad')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener la sucursal de la actividad
        cursor.execute("""
            SELECT id_sucursalactiva
            FROM tarja_fact_actividad
            WHERE id = %s
        """, (id_actividad,))
        actividad = cursor.fetchone()
        if not actividad or not actividad['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal de la actividad"}), 400
        id_sucursal = actividad['id_sucursalactiva']
        # Obtener los cuarteles filtrados por variedad y sucursal
        if id_variedad:
            cursor.execute("""
                SELECT cu.id, cu.nombre, cu.id_variedad, cu.id_ceco
                FROM general_dim_cuartel cu
                JOIN general_dim_ceco ce ON cu.id_ceco = ce.id
                WHERE ce.id_sucursal = %s AND cu.id_variedad = %s
                ORDER BY cu.nombre ASC
            """, (id_sucursal, id_variedad))
        else:
            cursor.execute("""
                SELECT cu.id, cu.nombre, cu.id_variedad, cu.id_ceco
                FROM general_dim_cuartel cu
                JOIN general_dim_ceco ce ON cu.id_ceco = ce.id
                WHERE ce.id_sucursal = %s
                ORDER BY cu.nombre ASC
            """, (id_sucursal,))
        cuarteles = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(cuarteles), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener tipos de inversión disponibles para la sucursal de la actividad
@opciones_bp.route('/tiposinversion/actividad/<string:id_actividad>', methods=['GET'])
@jwt_required()
def obtener_tiposinversion_por_actividad(id_actividad):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener la sucursal de la actividad
        cursor.execute("SELECT id_sucursalactiva FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
        actividad = cursor.fetchone()
        if not actividad or not actividad['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal de la actividad"}), 400
        id_sucursal = actividad['id_sucursalactiva']
        # Tipos de inversión que tengan inversiones asociadas a cecos de la sucursal
        cursor.execute("""
            SELECT DISTINCT ti.id, ti.nombre
            FROM general_dim_tipoinversion ti
            JOIN general_dim_inversion i ON i.id_tipoinversion = ti.id
            JOIN general_dim_ceco c ON i.id_ceco = c.id
            WHERE c.id_sucursal = %s
            ORDER BY ti.nombre ASC
        """, (id_sucursal,))
        tipos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(tipos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener inversiones disponibles para la sucursal de la actividad y tipo de inversión
@opciones_bp.route('/inversiones/actividad/<string:id_actividad>/<int:id_tipoinversion>', methods=['GET'])
@jwt_required()
def obtener_inversiones_por_actividad(id_actividad, id_tipoinversion):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener la sucursal de la actividad
        cursor.execute("SELECT id_sucursalactiva FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
        actividad = cursor.fetchone()
        if not actividad or not actividad['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal de la actividad"}), 400
        id_sucursal = actividad['id_sucursalactiva']
        # Inversiones del tipo y sucursal
        cursor.execute("""
            SELECT i.id, i.nombre
            FROM general_dim_inversion i
            JOIN general_dim_ceco c ON i.id_ceco = c.id
            WHERE i.id_tipoinversion = %s AND c.id_sucursal = %s
            ORDER BY i.nombre ASC
        """, (id_tipoinversion, id_sucursal))
        inversiones = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(inversiones), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener CECOs disponibles para la sucursal de la actividad, tipo de inversión e inversión
@opciones_bp.route('/cecosinversion/actividad/<string:id_actividad>/<int:id_tipoinversion>/<string:id_inversion>', methods=['GET'])
@jwt_required()
def obtener_cecosinversion_por_actividad(id_actividad, id_tipoinversion, id_inversion):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener la sucursal de la actividad
        cursor.execute("SELECT id_sucursalactiva FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
        actividad = cursor.fetchone()
        if not actividad or not actividad['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal de la actividad"}), 400
        id_sucursal = actividad['id_sucursalactiva']
        # CECOs asociados a la inversión y sucursal
        cursor.execute("""
            SELECT c.id, c.nombre
            FROM general_dim_ceco c
            JOIN general_dim_inversion i ON i.id_ceco = c.id
            WHERE i.id = %s AND i.id_tipoinversion = %s AND c.id_sucursal = %s
            ORDER BY c.nombre ASC
        """, (id_inversion, id_tipoinversion, id_sucursal))
        cecos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(cecos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener tipos de maquinaria
@opciones_bp.route('/tiposmaquinaria', methods=['GET'])
@jwt_required()
def obtener_tipos_maquinaria():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre FROM general_dim_maquinariatipo ORDER BY nombre ASC")
        tipos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(tipos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener maquinarias disponibles para la sucursal de la actividad y tipo de maquinaria
@opciones_bp.route('/maquinarias/actividad/<string:id_actividad>/<int:id_tipomaquinaria>', methods=['GET'])
@jwt_required()
def obtener_maquinarias_por_actividad_y_tipo(id_actividad, id_tipomaquinaria):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener la sucursal de la actividad
        cursor.execute("SELECT id_sucursalactiva FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
        actividad = cursor.fetchone()
        if not actividad or not actividad['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal de la actividad"}), 400
        id_sucursal = actividad['id_sucursalactiva']
        # Maquinarias del tipo y sucursal
        cursor.execute("""
            SELECT m.id, m.nombre
            FROM general_dim_maquinaria m
            JOIN general_dim_ceco c ON m.id_ceco = c.id
            WHERE m.id_maquinariatipo = %s AND c.id_sucursal = %s
            ORDER BY m.nombre ASC
        """, (id_tipomaquinaria, id_sucursal))
        maquinarias = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(maquinarias), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener CECOs disponibles para la sucursal de la actividad, tipo de maquinaria y maquinaria
@opciones_bp.route('/cecosmaquinaria/actividad/<string:id_actividad>/<int:id_tipomaquinaria>/<int:id_maquinaria>', methods=['GET'])
@jwt_required()
def obtener_cecosmaquinaria_por_actividad(id_actividad, id_tipomaquinaria, id_maquinaria):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener la sucursal de la actividad
        cursor.execute("SELECT id_sucursalactiva FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
        actividad = cursor.fetchone()
        if not actividad or not actividad['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal de la actividad"}), 400
        id_sucursal = actividad['id_sucursalactiva']
        # CECOs asociados a la maquinaria y sucursal
        cursor.execute("""
            SELECT c.id, c.nombre
            FROM general_dim_ceco c
            JOIN general_dim_maquinaria m ON m.id_ceco = c.id
            WHERE m.id = %s AND m.id_maquinariatipo = %s AND c.id_sucursal = %s
            ORDER BY c.nombre ASC
        """, (id_maquinaria, id_tipomaquinaria, id_sucursal))
        cecos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(cecos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@opciones_bp.route('/unidades', methods=['GET'])
@jwt_required()
def obtener_unidades():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nombre
            FROM tarja_dim_unidad
            WHERE id_estado = 1
            ORDER BY nombre ASC
        """)
        unidades = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(unidades), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener unidad por defecto de una labor específica
@opciones_bp.route('/labor/<string:id_labor>/unidad-default', methods=['GET'])
@jwt_required()
def obtener_unidad_default_labor(id_labor):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener la unidad por defecto de la labor
        cursor.execute("""
            SELECT l.id_unidadpordefecto, u.id, u.nombre
            FROM general_dim_labor l
            LEFT JOIN tarja_dim_unidad u ON l.id_unidadpordefecto = u.id
            WHERE l.id = %s
        """, (id_labor,))
        
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not resultado:
            return jsonify({"error": "Labor no encontrada"}), 404
        
        # Si la labor no tiene unidad por defecto, devolver null
        if not resultado['id_unidadpordefecto']:
            return jsonify({
                "id_unidad_default": None,
                "unidad_default": None
            }), 200
        
        return jsonify({
            "id_unidad_default": resultado['id'],
            "unidad_default": {
                "id": resultado['id'],
                "nombre": resultado['nombre']
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener lista de porcentajes de contratista
@opciones_bp.route('/porcentajescontratista', methods=['GET'])
@jwt_required()
def get_porcentajes_contratista():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, porcentaje, id_empresa
            FROM general_dim_porcentajecontratista
            ORDER BY porcentaje ASC
        """)
        porcentajes = cursor.fetchall()
        return jsonify([{
            'id': p[0],
            'porcentaje': p[1],
            'id_empresa': p[2]
        } for p in porcentajes]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Obtener tipos de maquinaria disponibles para la sucursal de la actividad
@opciones_bp.route('/tiposmaquinaria/actividad/<string:id_actividad>', methods=['GET'])
@jwt_required()
def obtener_tiposmaquinaria_por_actividad(id_actividad):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener la sucursal de la actividad
        cursor.execute("SELECT id_sucursalactiva FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
        actividad = cursor.fetchone()
        if not actividad or not actividad['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal de la actividad"}), 400
        id_sucursal = actividad['id_sucursalactiva']
        # Tipos de maquinaria que tengan maquinarias asociadas a cecos de la sucursal
        cursor.execute("""
            SELECT DISTINCT mt.id, mt.nombre
            FROM general_dim_maquinariatipo mt
            JOIN general_dim_maquinaria m ON m.id_maquinariatipo = mt.id
            JOIN general_dim_ceco c ON m.id_ceco = c.id
            WHERE c.id_sucursal = %s
            ORDER BY mt.nombre ASC
        """, (id_sucursal,))
        tipos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(tipos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener especies disponibles para la sucursal de la actividad
@opciones_bp.route('/especies/actividad/<string:id_actividad>', methods=['GET'])
@jwt_required()
def obtener_especies_por_actividad(id_actividad):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener la sucursal de la actividad
        cursor.execute("SELECT id_sucursalactiva FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
        actividad = cursor.fetchone()
        if not actividad or not actividad['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal de la actividad"}), 400
        id_sucursal = actividad['id_sucursalactiva']
        # Especies que tienen variedades asociadas a cuarteles de la sucursal
        cursor.execute("""
            SELECT DISTINCT e.id, e.nombre
            FROM general_dim_especie e
            JOIN general_dim_variedad v ON v.id_especie = e.id
            JOIN general_dim_cuartel c ON c.id_variedad = v.id
            JOIN general_dim_ceco ce ON c.id_ceco = ce.id
            WHERE ce.id_sucursal = %s
            ORDER BY e.nombre ASC
        """, (id_sucursal,))
        especies = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(especies), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener variedades disponibles para la sucursal de la actividad y especie
@opciones_bp.route('/variedades/actividad/<string:id_actividad>/<int:id_especie>', methods=['GET'])
@jwt_required()
def obtener_variedades_por_actividad(id_actividad, id_especie):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener la sucursal de la actividad
        cursor.execute("SELECT id_sucursalactiva FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
        actividad = cursor.fetchone()
        if not actividad or not actividad['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal de la actividad"}), 400
        id_sucursal = actividad['id_sucursalactiva']
        # Variedades de la especie que tienen cuarteles en la sucursal
        cursor.execute("""
            SELECT DISTINCT v.id, v.nombre
            FROM general_dim_variedad v
            JOIN general_dim_cuartel c ON c.id_variedad = v.id
            JOIN general_dim_ceco ce ON c.id_ceco = ce.id
            WHERE v.id_especie = %s AND ce.id_sucursal = %s
            ORDER BY v.nombre ASC
        """, (id_especie, id_sucursal))
        variedades = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(variedades), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener cuarteles disponibles para la sucursal de la actividad, especie y variedad
@opciones_bp.route('/cuarteles/actividad/<string:id_actividad>/<int:id_especie>/<int:id_variedad>', methods=['GET'])
@jwt_required()
def obtener_cuarteles_por_actividad_y_variedad(id_actividad, id_especie, id_variedad):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener la sucursal de la actividad
        cursor.execute("SELECT id_sucursalactiva FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
        actividad = cursor.fetchone()
        if not actividad or not actividad['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal de la actividad"}), 400
        id_sucursal = actividad['id_sucursalactiva']
        # Cuarteles de la variedad en la sucursal
        cursor.execute("""
            SELECT c.id, c.nombre
            FROM general_dim_cuartel c
            JOIN general_dim_ceco ce ON c.id_ceco = ce.id
            WHERE c.id_variedad = %s AND ce.id_sucursal = %s
            ORDER BY c.nombre ASC
        """, (id_variedad, id_sucursal))
        cuarteles = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(cuarteles), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener CECOs disponibles para la sucursal de la actividad, especie, variedad y cuartel
@opciones_bp.route('/cecosproductivo/actividad/<string:id_actividad>/<int:id_especie>/<int:id_variedad>/<int:id_cuartel>', methods=['GET'])
@jwt_required()
def obtener_cecosproductivo_por_actividad(id_actividad, id_especie, id_variedad, id_cuartel):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener el CECO asociado al cuartel seleccionado
        cursor.execute("""
            SELECT c.id, c.nombre
            FROM general_dim_ceco c
            JOIN general_dim_cuartel cu ON cu.id_ceco = c.id
            WHERE cu.id = %s
        """, (id_cuartel,))
        cecos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(cecos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
