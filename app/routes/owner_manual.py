from fastapi import APIRouter
from pydantic import BaseModel
from app.services.rag_service import get_answer

router = APIRouter()

class Query(BaseModel):
    brand: str
    model: str
    year: int
    question: str


@router.post("/owner-manual/query")
def query_owner_manual(q: Query):
    return get_answer(
        question=q.question,
        # year=q.year,
        # brand=q.brand,
        # model=q.model
        year=2020,
        brand="FIAT",  
        model="123 Spider"
    )