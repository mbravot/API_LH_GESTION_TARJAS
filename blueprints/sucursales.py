from flask import Blueprint, jsonify
from utils.db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

sucursales_bp = Blueprint('sucursales_bp', __name__)

@sucursales_bp.route('/ubicacion-activa', methods=['GET'])
@jwt_required()
def obtener_ubicacion_sucursal_activa():
    """Obtener la ubicación de la sucursal activa del usuario autenticado"""
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
        
        # Obtener la ubicación de la sucursal activa
        cursor.execute("""
            SELECT ubicacion FROM general_dim_sucursal 
            WHERE id = %s
        """, (id_sucursal,))
        
        sucursal = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not sucursal:
            return jsonify({"error": "Sucursal no encontrada"}), 404
            
        return jsonify({"ubicacion": sucursal['ubicacion']}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
