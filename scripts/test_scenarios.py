#!/usr/bin/env python3
"""
Scripts para probar escenarios específicos del sistema.
"""

from load_test import SimpleOrderTester


def test_normal_scenario():
    """Prueba con external service funcionando normal."""
    print("\nTESTING NORMAL SCENARIO")
    tester = SimpleOrderTester(num_orders=10)
    tester.create_orders(failure_mode="normal")

def test_slow_scenario():
    """Prueba con external service lento."""
    print("\nTESTING SLOW SCENARIO")
    tester = SimpleOrderTester(num_orders=5)
    tester.create_orders(failure_mode="slow")

def test_down_scenario():
    """Prueba con external service DOWN."""
    print("\nTESTING DOWN SCENARIO")
    tester = SimpleOrderTester(num_orders=5)
    tester.create_orders(failure_mode="down")

def test_error_scenario():
    """Prueba con external service devolviendo errores 500."""
    print("\nTESTING ERROR SCENARIO")
    tester = SimpleOrderTester(num_orders=5)
    tester.create_orders(failure_mode="error")