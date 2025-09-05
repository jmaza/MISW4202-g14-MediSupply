from enum import StrEnum

class FailureMode(StrEnum):
    NORMAL = "normal"
    DOWN = "down"
    SLOW = "slow"
    ERROR = "error"