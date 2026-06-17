from pydantic import BaseModel


class FieldStatus(BaseModel):
    field_name: str
    value: str | None
    display_value: str
    unit: str | None = None
    reference_range: str | None = None
    ref_low: float | None = None
    ref_high: float | None = None
    numeric_value: float | None = None
    patient_verified: bool = False
    doctor_verified: bool = False
    is_final: bool = False
    eda_available: bool = False

    @property
    def is_value_hidden(self) -> bool:
        return False


