from pydantic import BaseModel, Field


class CleaningOptions(BaseModel):
    missing_strategy: str = Field(default="keep", pattern="^(keep|drop_rows|fill_zero|fill_mean|fill_median)$")
    remove_duplicates: bool = True
    standardize_dates: bool = True
    coerce_invalid_numbers: bool = True
