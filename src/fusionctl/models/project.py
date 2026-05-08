from pydantic import BaseModel, Field


class Project(BaseModel):
    """Oracle project reference."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    active: bool = True


class Task(BaseModel):
    """Oracle task reference."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    active: bool = True
