from enum import StrEnum

class OrderStatus(StrEnum):
    PENDING = "Pending"
    VALIDATED = "Validated"
    REJECTED = "Rejected"