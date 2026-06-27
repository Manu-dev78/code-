from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from heuristics import analyze_code
from nlp import analyze_with_nlp
from ml_weighting import combine_scores
from fastapi import BackgroundTasks
from database import supabase
import asyncio


def save_scan_to_db(code: str, language: str, ai_probability: float, details: dict, prompt: str = None):
    if not supabase:
        return
    try:
        data = {
            "code": code,
            "prompt": prompt,
            "language": language,
            "ai_probability": ai_probability,
            "details": details
        }
        supabase.table("scan_history").insert(data).execute()
    except Exception as e:
        print(f"Error saving to db: {e}")


app = FastAPI(title="AI Code Detector API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CodeRequest(BaseModel):
    code: str
    language: str = "python"



class AnalysisResponse(BaseModel):
    ai_probability: float
    details: dict


async def run_analysis(code: str, language: str):
    heuristic_result = await asyncio.to_thread(analyze_code, code, language)
    nlp_result = await asyncio.to_thread(analyze_with_nlp, code)

    # Use ML-based dynamic weighting
    return combine_scores(heuristic_result, nlp_result)


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: CodeRequest, background_tasks: BackgroundTasks):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")

    combined_result = await run_analysis(request.code, request.language)

    background_tasks.add_task(
        save_scan_to_db, 
        request.code, request.language, 
        combined_result["ai_probability"], combined_result["details"]
    )


    return combined_result



@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/history")
async def get_history():
    if not supabase:
        return []
    try:
        response = supabase.table("scan_history").select("*").order("created_at", desc=True).limit(50).execute()
        return response.data
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []
