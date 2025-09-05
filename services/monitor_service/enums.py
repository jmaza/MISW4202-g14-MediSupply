from enum import StrEnum

class HealthStatus(StrEnum):
    HEALTHY = "healthy"        # Funcionando correctamente
    DEGRADED = "degraded"      # Funciona pero con problemas
    UNHEALTHY = "unhealthy"    # Con errores pero responde
    DOWN = "down"              # No responde/no disponible
    CRITICAL = "critical"      # Estado crítico (solo para sistema general)
    UNKNOWN = "unknown"        # Estado desconocido

