from flask import Flask, jsonify
import redis
import requests
import time
import logging
from datetime import datetime
from requests import codes
from enums import HealthStatus
import threading
import schedule
import json

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
        response = requests.get(url, timeout=15)
        response_time = response.elapsed.total_seconds()
        
        if response.status_code == codes.OK:
            return {
                "status": HealthStatus.HEALTHY, 
                "response_time": response_time,
                "service": service_name
            }
        elif response.status_code == codes.GATEWAY_TIMEOUT:
            return {
                "status": HealthStatus.DEGRADED, 
                "error": "Service running slow",
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

def check_all_services():
    """Verifica todos los servicios una vez."""
    try:
        timestamp = datetime.now().isoformat()
        results = {}
        
        for service_name, url in SERVICES.items():
            health = check_service_health(service_name, url)
            results[service_name] = health
            
            # Log solo cambios de estado o fallas
            if health["status"] != HealthStatus.HEALTHY:
                logger.warning(f"{service_name}: {health['status']} - {health.get('error', '')}")
        
        # Almacenar resultados en Redis
        redis_client.setex("health_status", 300, json.dumps({
            "timestamp": timestamp,
            "services": results
        }))
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")

def run_scheduler():
    """Ejecuta el scheduler en un hilo separado."""
    schedule.every(30).seconds.do(check_all_services)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

@app.route("/health_status", methods=["GET"])
def get_health_status():
    """Obtiene el estado actual de todos los servicios."""
    try:
        status = redis_client.get("health_status")
        if status:
            return jsonify(json.loads(status)), codes.OK
        else:
            return jsonify({"error": "No health data available"}), codes.NOT_FOUND
    except Exception as e:
        return jsonify({"error": str(e)}), codes.INTERNAL_SERVER_ERROR

@app.route("/health", methods=["GET"])
def health_check():
    """Health check del propio monitor service."""
    try:
        redis_client.ping()
        return jsonify({
            "service": "monitor_service",
            "status": HealthStatus.HEALTHY,
            "timestamp": datetime.now().isoformat()
        }), codes.OK
    except Exception as e:
        return jsonify({
            "service": "monitor_service",
            "status": HealthStatus.DOWN,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), codes.SERVICE_UNAVAILABLE

if __name__ == "__main__":
    logger.info("Monitor Service starting...")
    
    # Iniciar scheduler en hilo separado
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Periodic health checks started (every 30 seconds)")
    
    app.run(debug=True, host="0.0.0.0", port=5004)
