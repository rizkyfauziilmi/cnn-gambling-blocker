from dataclasses import dataclass
from typing import Literal

# Definisikan type alias untuk mempermudah pembacaan
StatusType = Literal["success", "error"]
LabelType = Literal["JUDI", "BUKAN JUDI", "UNKNOWN"]


@dataclass
class PredictionResult:
    # Status hanya boleh berisi string "success" atau "error"
    status: StatusType

    # Label juga bisa kita buat strong type agar tidak typo
    label: LabelType

    confidence: float
    is_gambling: bool

    # Message hanya ada jika status == "error"
    message: str | None = None
