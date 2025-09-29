from flask import Flask, request, jsonify
import requests
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

@app.route("/create_order", methods=["POST"])
def proxy_create_order():
    """Proxy simple hacia Order Service"""
    try:
        response = requests.post(
            "http://order_service:5001/create_order",
            json=request.get_json(),
            timeout=5
        )
        return response.json(), response.status_code
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Service timeout'}), 504
    except Exception as e:
        logger.error(f"Gateway error: {e}")
        return jsonify({'error': 'Internal error'}), 500

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"service": "api_gateway", "status": "healthy"}), 200

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=8080)
