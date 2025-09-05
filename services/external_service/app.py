from flask import Flask, request, jsonify
import random
import time
import os
from requests import codes
from enums import FailureMode

app = Flask(__name__)

# Variables de control para simular fallas
FAILURE_MODE = os.getenv("FAILURE_MODE", FailureMode.NORMAL)

@app.route("/validate", methods=["POST"])
def validate_order():
    """Simula validación de pedido con posibles fallas."""
    
    # Simular caída total
    if FAILURE_MODE == FailureMode.DOWN:
        return jsonify({"error": "Service unavailable"}), codes.SERVICE_UNAVAILABLE
    
    # Simular lentitud
    if FAILURE_MODE == FailureMode.SLOW:
        time.sleep(10)
    
    # Simular respuestas erróneas (100% errores)
    if FAILURE_MODE == FailureMode.ERROR:
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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5002)
