#!/usr/bin/env python3
"""
Script simple para crear órdenes y cambiar modos de falla.
"""

import requests
import time
import uuid
import argparse

# URLs de los servicios
ORDER_SERVICE_URL = "http://localhost:5001"
EXTERNAL_SERVICE_URL = "http://localhost:5003"

class SimpleOrderTester:
    def __init__(self, num_orders=10):
        self.num_orders = num_orders
        
    def create_order(self, order_id):
        """Crea una orden individual."""
        try:
            response = requests.post(
                f"{ORDER_SERVICE_URL}/create_order",
                json={
                    "order_id": order_id,
                    "product": "Test Product",
                    "quantity": 5
                },
            )
            
            if response.status_code == 200:
                print(f"✅ Order {order_id} created")
                return True
            else:
                print(f"❌ Order {order_id} failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Order {order_id} error: {e}")
            return False
    
    def set_failure_mode(self, mode):
        """Cambia el modo de fallas del external service."""
        try:
            response = requests.post(
                f"{EXTERNAL_SERVICE_URL}/set_failure_mode",
                json={"mode": mode},
                timeout=5
            )
            if response.status_code == 200:
                print(f"✅ Failure mode set to: {mode}")
                return True
            else:
                print(f"❌ Failed to set failure mode: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error setting failure mode: {e}")
            return False
    
    def create_orders(self, failure_mode="normal"):
        """Crea las órdenes secuencialmente."""
        print(f"\n🔧 Setting failure mode to: {failure_mode}")
        if not self.set_failure_mode(failure_mode):
            return
        
        print(f"\n📦 Creating {self.num_orders} orders...")
        
        successful = 0
        for i in range(self.num_orders):
            order_id = f"simple-test-{uuid.uuid4().hex[:8]}"
            if self.create_order(order_id):
                successful += 1
            time.sleep(0.5)
        
        print(f"\n📊 Summary: {successful}/{self.num_orders} orders created successfully")


def clear_database():
    """Elimina todas las órdenes de la base de datos."""
    try:
        response = requests.delete(f"{ORDER_SERVICE_URL}/clear_orders", timeout=5)
        if response.status_code == 200:
            print("   ✅ Database cleared")
            return True
        else:
            print("   ❌ Failed to clear database")
            return False
    except Exception as e:
        print(f"   ❌ Error clearing database: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Simple order creator")
    parser.add_argument("--orders", type=int, default=10, help="Number of orders to create")
    parser.add_argument("--mode", default="normal", choices=["normal", "slow", "down", "error"], 
                       help="Failure mode for external service")
    
    args = parser.parse_args()
    
    tester = SimpleOrderTester(num_orders=args.orders)
    tester.create_orders(failure_mode=args.mode)

if __name__ == "__main__":
    clear_database()
    main()
