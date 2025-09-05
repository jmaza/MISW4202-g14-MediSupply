from flask import Flask, request, jsonify
import sqlite3
import redis
from rq import Queue
from enums import OrderStatus
from requests import codes
from datetime import datetime

# Configuración de Flask
app = Flask(__name__)

# Conexión a Redis
redis_client = redis.StrictRedis(host="redis", port=6379, db=0)

# Crear una cola de mensajes con Redis
queue = Queue(connection=redis_client)

# Ruta a la base de datos SQLite
DATABASE = "data/db.sqlite"

def init_db():
    """Inicializa la base de datos SQLite si no existe."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    product TEXT,
                    quantity INTEGER,
                    status TEXT)''')
    conn.commit()
    conn.close()

@app.route("/create_order", methods=["POST"])
def create_order():
    """Crea un nuevo pedido, lo guarda en SQLite y lo publica en la cola de Redis con RQ."""
    data = request.get_json()
    order_id = data.get("order_id")
    product = data.get("product")
    quantity = data.get("quantity")

    # Guardar el pedido en SQLite
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO orders (order_id, product, quantity, status) VALUES (?, ?, ?, ?)",
              (order_id, product, quantity, OrderStatus.PENDING))
    conn.commit()
    conn.close()

    # Publicar el pedido en la cola usando RQ - encolar datos, no función específica
    queue.enqueue("app.process_order_validation", {
        "order_id": order_id,
        "product": product,
        "quantity": quantity
    })

    return jsonify({"message": "Order placed successfully!"}), codes.OK

@app.route("/get_orders", methods=["GET"])
def get_orders():
    """Devuelve todos los pedidos almacenados en la base de datos SQLite."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM orders")
    orders = c.fetchall()
    conn.close()

    return jsonify({"orders": orders}), codes.OK

@app.route("/health", methods=["GET"])
def health_check():
    """Readiness check - verifica que el servicio puede procesar órdenes."""
    try:
        # Verificar Redis (crítico para el funcionamiento)
        redis_client.ping()
        
        # Verificar base de datos
        conn = sqlite3.connect(DATABASE)
        conn.close()
        
        return jsonify({
            "service": "order_service",
            "status": codes.OK,
            "timestamp": datetime.now().isoformat()
        }), codes.OK
    except Exception as e:
        return jsonify({
            "service": "order_service",
            "status": codes.SERVICE_UNAVAILABLE,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), codes.SERVICE_UNAVAILABLE

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5001)
