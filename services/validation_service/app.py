from flask import Flask, jsonify
import sqlite3
import redis
import requests
from rq import Worker, Queue
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError, retry_if_exception_type
from enums import OrderStatus
from datetime import datetime
from requests import codes
from pybreaker import CircuitBreaker, CircuitBreakerError

app = Flask(__name__)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conexión a Redis
redis_client = redis.StrictRedis(host="redis", port=6379, db=0)
queue = Queue(connection=redis_client)

DATABASE = "data/db.sqlite"

# Circuit Breaker configurado
external_breaker = CircuitBreaker(
    fail_max=3,
    reset_timeout=30,
    exclude=[requests.exceptions.Timeout]
)

@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.exceptions.Timeout)  # Solo reintentar timeouts
)
@external_breaker
def call_external_service(order_data):
    """Llamada protegida al servicio externo con reintentos."""
    order_id = order_data.get("order_id", "unknown")
    logger.info(f"Attempting validation for order {order_id} - calling external service")
    
    try:
        response = requests.post(
            "http://external_service:5003/validate", 
            json=order_data,
            timeout=5
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"External service responded for order {order_id}: {result}")
        return result
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout calling external service for order {order_id} (will retry)")
        raise
    except requests.exceptions.HTTPError as e:
        if e.response.status_code >= 500:
            logger.error(f"Server error {e.response.status_code} for order {order_id} - service DOWN")
            raise requests.exceptions.ConnectionError("Service DOWN")  # No reintenta
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Connection error for order {order_id}: {e} - service DOWN")
        raise requests.exceptions.ConnectionError("Service DOWN")  # No reintenta

def update_order_status(order_id, status):
    """Actualiza el estado de una orden en la base de datos."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))
    conn.commit()
    conn.close()

def process_order_validation(order_data):
    """Procesa la validación del pedido - función llamada por RQ worker."""
    order_id = order_data["order_id"]
    logger.info(f"Starting validation process for order {order_id}")
    
    try:
        # Intentar validación con circuit breaker
        validation_result = call_external_service(order_data)
        is_valid = validation_result.get("valid", False)
        status = OrderStatus.VALIDATED if is_valid else OrderStatus.REJECTED
        logger.info(f"Validation completed for order {order_id}: valid={is_valid}, status={status}")
        
    except CircuitBreakerError:
        # Circuit breaker OPEN - mantener como PROCESSING
        logger.warning(f"Circuit breaker is OPEN - Order {order_id} remains PROCESSING (will retry later)")
        return  # No cambiar estado, se reintentará después
        
    except RetryError as e:
        # Tenacity agotó reintentos - servicio lento
        logger.error(f"External service failed after 3 retry attempts for order {order_id} - marking as REJECTED")
        logger.debug(f"RetryError details for order {order_id}: {e}")
        status = OrderStatus.REJECTED
        
    except (requests.exceptions.ConnectionError, requests.exceptions.RequestException, 
            sqlite3.Error, Exception) as e:
        if isinstance(e, requests.exceptions.ConnectionError):
            logger.error(f"External service is DOWN for order {order_id}: {e}")
        elif isinstance(e, requests.exceptions.RequestException):
            logger.error(f"External service communication error for order {order_id}: {type(e).__name__} - {e}")
        elif isinstance(e, sqlite3.Error):
            logger.error(f"Database error while processing order {order_id}: {e}")
        else:
            logger.error(f"Unexpected internal error processing order {order_id}: {type(e).__name__} - {e}")
        
        status = OrderStatus.FAILED
    
    # Actualizar estado
    try:
        update_order_status(order_id, status)
        logger.info(f"Order {order_id} validation completed - final status: {status}")
    except Exception as e:
        logger.error(f"Failed to update database status for order {order_id}: {e}")

def start_worker():
    """Inicia el worker de RQ para procesar los pedidos."""
    worker = Worker([queue], connection=redis_client)
    worker.work()

@app.route("/health", methods=["GET"])
def health_check():
    """Health check del validation service."""
    try:
        redis_client.ping()
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
