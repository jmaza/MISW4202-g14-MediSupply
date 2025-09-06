from flask import Flask, request, jsonify
import time
import os
from requests import codes
from enums import FailureMode
from datetime import datetime
import logging

app = Flask(__name__)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Estado dinámico del simulador
current_failure_mode = FailureMode.NORMAL

@app.route("/set_failure_mode", methods=["POST"])
def set_failure_mode():
    """Cambia el modo de fallas dinámicamente."""
    global current_failure_mode
    
    data = request.get_json()
    mode = data.get("mode", FailureMode.NORMAL).upper()
    
    # Validar modo
    if hasattr(FailureMode, mode):
        current_failure_mode = getattr(FailureMode, mode)
        logger.info(f"Failure mode changed to: {current_failure_mode}")
        return jsonify({
            "status": "success", 
            "mode": current_failure_mode
        }), codes.OK
    else:
        return jsonify({"error": f"Invalid mode. Valid: {list(FailureMode)}"}), codes.BAD_REQUEST

@app.route("/get_failure_mode", methods=["GET"])
def get_failure_mode():
    """Obtiene el modo actual de fallas."""
    return jsonify({"mode": current_failure_mode}), codes.OK

@app.route("/validate", methods=["POST"])
def validate_order():
    """Simula validación de pedido con posibles fallas."""
    
    # Simular caída total
    if current_failure_mode == FailureMode.DOWN:
        return jsonify({"error": "Service unavailable"}), codes.SERVICE_UNAVAILABLE
    
    # Simular lentitud
    if current_failure_mode == FailureMode.SLOW:
        time.sleep(10)
    
    # Simular respuestas erróneas (100% errores)
    if current_failure_mode == FailureMode.ERROR:
        return jsonify({"error": "Validation failed"}), codes.INTERNAL_SERVER_ERROR
    
    # Comportamiento normal
    order_data = request.get_json()
    order_id = order_data.get("order_id")
    
    # Simular validación (100% válidos)
    is_valid = True
    
    return jsonify({
        "order_id": order_id,
        "valid": is_valid,
        "message": "Order validated successfully" if is_valid else "Order rejected"
    }), codes.OK

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint para el monitor."""
    if current_failure_mode in [FailureMode.DOWN, FailureMode.ERROR]:
        return jsonify({
            "service": "external_service",
            "status": codes.SERVICE_UNAVAILABLE,
            "error": "Service unavailable",
            "timestamp": datetime.now().isoformat()
        }), codes.SERVICE_UNAVAILABLE
    
    if current_failure_mode == FailureMode.SLOW:
        return jsonify({
            "service": "external_service", 
            "status": codes.GATEWAY_TIMEOUT,
            "timestamp": datetime.now().isoformat(),
        }), codes.GATEWAY_TIMEOUT
    
    return jsonify({
        "service": "external_service", 
        "status": codes.OK,
        "timestamp": datetime.now().isoformat()
    }), codes.OK

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5003)
