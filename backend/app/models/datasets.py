from typing import Literal

from pydantic import BaseModel, model_validator


class CleaningOptions(BaseModel):
    missing_strategy: Literal["keep", "drop_rows", "fill_zero", "fill_mean", "fill_median", "fill_mode", "fill_custom"] = "keep"
    custom_value: str | None = None
    remove_duplicates: bool = True
    standardize_dates: bool = True
    coerce_invalid_numbers: bool = True

    @model_validator(mode="after")
    def require_custom_value(self):
        if self.missing_strategy == "fill_custom" and (self.custom_value is None or not self.custom_value.strip()):
            raise ValueError("Enter a custom value before previewing or applying this strategy.")
        return self
