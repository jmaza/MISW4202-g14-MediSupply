from flask import Flask, jsonify
import sqlite3
import redis
import requests
from rq import Worker, Queue
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from enums import OrderStatus
from datetime import datetime
from requests import codes

app = Flask(__name__)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conexión a Redis
redis_client = redis.StrictRedis(host="redis", port=6379, db=0)
queue = Queue(connection=redis_client)

DATABASE = "data/db.sqlite"
EXTERNAL_SERVICE_URL = "http://external_service:5003/validate"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_external_service(order_data):
    """Llama al servicio externo con reintentos y backoff."""
    try:
        response = requests.post(EXTERNAL_SERVICE_URL, json=order_data, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling external service: {e}")
        raise

def process_order_validation(order_data):
    """Procesa la validación del pedido."""
    order_id = order_data["order_id"]
    logger.info(f"Processing validation for order {order_id}")
    
    try:
        # Llamar al servicio externo
        validation_result = call_external_service(order_data)
        status = OrderStatus.VALIDATED if validation_result.get("valid", False) else OrderStatus.REJECTED
        
    except Exception as e:
        logger.error(f"Failed to validate order {order_id}: {e}")
        status = OrderStatus.REJECTED
    
    # Actualizar estado en base de datos
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))
    conn.commit()
    conn.close()
    
    logger.info(f"Order {order_id} processed with status: {status}")

def start_worker():
    """Inicia el worker de RQ para procesar los pedidos."""
    worker = Worker([queue], connection=redis_client)
    worker.work()

@app.route("/health", methods=["GET"])
def health_check():
    """Readiness check - verifica que el servicio puede validar órdenes."""
    try:
        # Verificar Redis (crítico para RQ)
        redis_client.ping()
        
        # Verificar base de datos
        conn = sqlite3.connect(DATABASE)
        conn.close()
        
        return jsonify({
            "service": "validation_service", 
            "status": codes.OK,
            "timestamp": datetime.now().isoformat()
        }), codes.OK
    except Exception as e:
        return jsonify({
            "service": "validation_service",
            "status": codes.SERVICE_UNAVAILABLE, 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), codes.SERVICE_UNAVAILABLE

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5002)
