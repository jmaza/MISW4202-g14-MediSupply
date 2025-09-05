from enum import StrEnum

class OrderStatus(StrEnum):
    VALIDATED = "Validated"
    REJECTED = "Rejected"
    PROCESSING = "Processing"
    FAILED = "Failed"