import asyncio
import aiohttp

from typing import Literal, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database import get_db
from backend.models.history import APIHistory, APIRequestCollection

from backend.services.request_engine import send_api_request
from backend.services.analyzer import analyze_response
from backend.services.ai_diagnosis import generate_ai_diagnosis
from backend.services.response_comparator import compare_json
from backend.services.code_fix_generator import generate_code_fix


router = APIRouter()


# ==========================================
# REQUEST MODELS
# ==========================================

class APIRequest(BaseModel):
    url: str

    method: Literal[
        "GET", "POST", "PUT", "PATCH", "DELETE"
    ] = "GET"

    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, str] = Field(default_factory=dict)
    json_body: Any = None


class CompareRequest(BaseModel):
    response_a: dict
    response_b: dict


class CodeFixRequest(BaseModel):
    analysis: dict

    language: Literal[
        "Python",
        "C",
        "C++",
        "Java",
        "JavaScript",
        "TypeScript",
        "PHP",
        "HTML",
        "SQL",
        "Go"
    ]


class CollectionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=1, max_length=1000)

    method: Literal[
        "GET", "POST", "PUT", "PATCH", "DELETE"
    ] = "GET"

    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, str] = Field(default_factory=dict)
    json_body: Any = None


# ==========================================
# HISTORY FORMATTER
# ==========================================

def format_history(record):

    return {
        "id": record.id,
        "url": record.url,
        "method": record.method,
        "status_code": record.status_code,
        "response_time_ms": record.response_time_ms,
        "health": record.health,
        "health_score": record.health_score,
        "json_valid": record.json_valid,
        "issues": record.issues,
        "suggestions": record.suggestions,
        "ai_diagnosis": record.ai_diagnosis,
        "created_at": (
            record.created_at.isoformat()
            if record.created_at else None
        )
    }


# ==========================================
# COLLECTION FORMATTER
# ==========================================

def format_collection(record):

    return {
        "id": record.id,
        "name": record.name,
        "url": record.url,
        "method": record.method,
        "headers": record.headers or {},
        "params": record.params or {},
        "json_body": record.json_body,
        "created_at": (
            record.created_at.isoformat()
            if record.created_at else None
        )
    }


# ==========================================
# API TESTING ENDPOINT
# ==========================================

@router.post("/test")
async def test_api(
    request: APIRequest,
    db: Session = Depends(get_db)
):

    try:

        # Send API request
        result = await send_api_request(
            url=request.url,
            method=request.method,
            headers=request.headers,
            params=request.params,
            json_data=request.json_body
        )

        # Analyse API response
        analysis = analyze_response(
            result["status_code"],
            result["response_time_ms"],
            result["headers"],
            result["body"]
        )

        # Generate AI diagnosis
        try:
            ai_diagnosis = await generate_ai_diagnosis(analysis)

        except Exception as ai_error:
            ai_diagnosis = (
                f"AI diagnosis unavailable: "
                f"{type(ai_error).__name__}"
            )

        # Save request history
        history = APIHistory(
            url=request.url,
            method=request.method,
            status_code=result["status_code"],
            response_time_ms=result["response_time_ms"],
            health=analysis.get("health"),
            health_score=analysis.get("health_score"),
            json_valid=analysis.get("json_valid"),
            issues=analysis.get("issues", []),
            suggestions=analysis.get("suggestions", []),
            ai_diagnosis=ai_diagnosis
        )

        db.add(history)
        db.commit()
        db.refresh(history)

        return {
            "success": True,
            "message": "API request completed successfully",
            "data": result,
            "analysis": analysis,
            "ai_diagnosis": ai_diagnosis,
            "history_id": history.id
        }

    except ValueError as error:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except asyncio.TimeoutError:
        db.rollback()
        raise HTTPException(
            status_code=408,
            detail="API request timed out"
        )

    except aiohttp.ClientError:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Unable to connect to the target API"
        )

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {type(error).__name__}"
        )


# ==========================================
# HISTORY ENDPOINT
# ==========================================

@router.get("/history")
def get_history(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100"
        )

    if offset < 0:
        raise HTTPException(
            status_code=400,
            detail="Offset cannot be negative"
        )

    records = (
        db.query(APIHistory)
        .order_by(
            desc(APIHistory.created_at),
            desc(APIHistory.id)
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "success": True,
        "count": len(records),
        "history": [
            format_history(record)
            for record in records
        ]
    }


# ==========================================
# SINGLE HISTORY ENDPOINT
# ==========================================

@router.get("/history/{history_id}")
def get_history_by_id(
    history_id: int,
    db: Session = Depends(get_db)
):

    record = (
        db.query(APIHistory)
        .filter(APIHistory.id == history_id)
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail="History record not found"
        )

    return {
        "success": True,
        "history": format_history(record)
    }


# ==========================================
# JSON COMPARISON ENDPOINT
# ==========================================

@router.post("/compare")
def compare_responses(request: CompareRequest):

    try:

        comparison = compare_json(
            request.response_a,
            request.response_b
        )

        return {
            "success": True,
            "message": "Response comparison completed",
            "comparison": comparison
        }

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Unable to compare JSON responses"
        )


# ==========================================
# AI CODE FIX GENERATOR
# ==========================================

@router.post("/generate-fix")
async def generate_fix(request: CodeFixRequest):

    try:

        code_fix = await generate_code_fix(
            request.analysis,
            request.language
        )

        return {
            "success": True,
            "message": "AI code fix generated successfully",
            "language": request.language,
            "code_fix": code_fix
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=(
                f"AI code generation failed: "
                f"{type(error).__name__}"
            )
        )


# ==========================================
# DASHBOARD ANALYTICS
# ==========================================

@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):

    records = (
        db.query(APIHistory)
        .order_by(
            desc(APIHistory.created_at),
            desc(APIHistory.id)
        )
        .limit(500)
        .all()
    )

    total = len(records)

    successful = sum(
        1 for record in records
        if record.status_code is not None
        and 200 <= record.status_code < 400
    )

    failed = total - successful

    scores = [
        record.health_score
        for record in records
        if record.health_score is not None
    ]

    times = [
        record.response_time_ms
        for record in records
        if record.response_time_ms is not None
    ]

    return {
        "total_requests": total,
        "successful_requests": successful,
        "failed_requests": failed,

        "success_rate": (
            round((successful / total) * 100, 1)
            if total else 0
        ),

        "average_health_score": (
            round(sum(scores) / len(scores), 1)
            if scores else 0
        ),

        "average_response_time_ms": (
            round(sum(times) / len(times), 2)
            if times else 0
        ),

        "slow_requests": sum(
            1 for time in times if time > 1000
        ),

        "recent": [
            format_history(record)
            for record in records[:10]
        ]
    }


# ==========================================
# SAVED REQUEST COLLECTIONS
# ==========================================

@router.get("/collections")
def get_collections(db: Session = Depends(get_db)):

    items = (
        db.query(APIRequestCollection)
        .order_by(desc(APIRequestCollection.id))
        .all()
    )

    return {
        "collections": [
            format_collection(item)
            for item in items
        ]
    }


@router.post("/collections")
def create_collection(
    request: CollectionRequest,
    db: Session = Depends(get_db)
):

    name = request.name.strip()
    url = request.url.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Collection name cannot be empty"
        )

    if not url:
        raise HTTPException(
            status_code=400,
            detail="API URL cannot be empty"
        )

    item = APIRequestCollection(
        name=name,
        url=url,
        method=request.method,
        headers=request.headers,
        params=request.params,
        json_body=request.json_body
    )

    try:
        db.add(item)
        db.commit()
        db.refresh(item)

        return {
            "success": True,
            "collection": format_collection(item)
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to save API request"
        )


@router.delete("/collections/{collection_id}")
def delete_collection(
    collection_id: int,
    db: Session = Depends(get_db)
):

    item = (
        db.query(APIRequestCollection)
        .filter(APIRequestCollection.id == collection_id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Saved request not found"
        )

    try:
        db.delete(item)
        db.commit()

        return {
            "success": True,
            "message": "Saved request deleted"
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to delete saved request"
        )