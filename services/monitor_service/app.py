from flask import Flask, jsonify
import redis
import requests
import time
import logging
from datetime import datetime
from requests import codes
from enums import HealthStatus

app = Flask(__name__)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connect to Redis
redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)

# URLs de los servicios a monitorear
SERVICES = {
    "order_service": "http://order_service:5001/health",
    "validation_service": "http://validation_service:5002/health",
    "external_service": "http://external_service:5003/health"
}

def check_service_health(service_name, url):
    """Verifica el estado de un servicio específico."""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == codes.OK:
            return {
                "status": HealthStatus.HEALTHY, 
                "response_time": response.elapsed.total_seconds(),
                "service": service_name
            }
        else:
            return {
                "status": HealthStatus.UNHEALTHY, 
                "error": f"HTTP {response.status_code}",
                "service": service_name
            }
    except requests.exceptions.RequestException as e:
        return {
            "status": HealthStatus.DOWN, 
            "error": str(e),
            "service": service_name
        }

def check_redis_health():
    """Verifica el estado de Redis."""
    try:
        redis_client.ping()
        queue_length = redis_client.llen("order_queue")
        return {
            "status": HealthStatus.HEALTHY,
            "queue_length": queue_length,
            "info": "Redis connection successful"
        }
    except Exception as e:
        return {"status": HealthStatus.DOWN, "error": str(e)}

@app.route("/monitor_health", methods=["GET"])
def monitor_health():
    """Endpoint principal de monitoreo."""
    health_report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": HealthStatus.HEALTHY,
        "services": {},
        "infrastructure": {}
    }
    
    # Verificar Redis
    redis_health = check_redis_health()
    health_report["infrastructure"]["redis"] = redis_health
    
    # Verificar cada servicio
    unhealthy_services = 0
    for service_name, url in SERVICES.items():
        service_health = check_service_health(service_name, url)
        health_report["services"][service_name] = service_health
        
        if service_health["status"] != HealthStatus.HEALTHY:
            unhealthy_services += 1
    
    # Determinar estado general
    if redis_health["status"] != HealthStatus.HEALTHY:
        health_report["overall_status"] = HealthStatus.CRITICAL
    elif unhealthy_services > 0:
        health_report["overall_status"] = HealthStatus.DEGRADED
    
    # Log del estado
    logger.info(f'Health check completed - Status: {health_report["overall_status"]}')
    
    # Código de respuesta HTTP basado en el estado
    status_code = codes.OK
    if health_report["overall_status"] == HealthStatus.CRITICAL:
        status_code = codes.SERVICE_UNAVAILABLE
    elif health_report["overall_status"] == HealthStatus.DEGRADED:
        status_code = codes.PARTIAL_CONTENT  # Partial Content
    
    return jsonify(health_report), status_code

@app.route("/monitor_metrics", methods=["GET"])
def monitor_metrics():
    """Endpoint para métricas específicas."""
    try:
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "redis": {
                "queue_length": redis_client.llen("order_queue"),
                "memory_usage": redis_client.info("memory").get("used_memory_human", "N/A"),
                "connected_clients": redis_client.info("clients").get("connected_clients", 0)
            },
            "system": {
                "uptime": time.time() - app.start_time if hasattr(app, "start_time") else 0
            }
        }
        return jsonify(metrics), codes.OK
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({"error": "Failed to get metrics"}), codes.INTERNAL_SERVER_ERROR

@app.route("/health", methods=["GET"])
def health_check():
    """Health check del propio monitor service."""
    try:
        # Verificar Redis (crítico para el monitor)
        redis_client.ping()
        
        return jsonify({
            "service": "monitor_service",
            "status": HealthStatus.HEALTHY,
            "timestamp": datetime.now().isoformat()
        }), codes.OK
        
    except redis.ConnectionError:
        return jsonify({
            "service": "monitor_service",
            "status": HealthStatus.DOWN,
            "error": "Redis connection failed",
            "timestamp": datetime.now().isoformat()
        }), codes.SERVICE_UNAVAILABLE
        
    except Exception as e:
        return jsonify({
            "service": "monitor_service",
            "status": HealthStatus.DEGRADED,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), codes.PARTIAL_CONTENT

if __name__ == "__main__":
    app.start_time = time.time()
    logger.info("Monitor Service starting...")
    app.run(debug=True, host="0.0.0.0", port=5004)
