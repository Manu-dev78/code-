from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from heuristics import analyze_code
from nlp import analyze_with_nlp
from prompt_engine import generate_code_from_prompt, check_ollama_status, get_active_provider
from similarity import compute_similarity, get_verdict
from ml_weighting import combine_scores
from fastapi import BackgroundTasks
from database import supabase
import asyncio

def save_scan_to_db(code: str, prompt: str, language: str, ai_probability: float, details: dict):
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


class PromptComparisonRequest(BaseModel):
    code: str
    prompt: str
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
        request.code, None, request.language, 
        combined_result["ai_probability"], combined_result["details"]
    )

    return combined_result


@app.post("/analyze/prompt")
async def analyze_with_prompt(request: PromptComparisonRequest, background_tasks: BackgroundTasks):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # Get base analysis first
    base_analysis = await run_analysis(request.code, request.language)
    base_prob = base_analysis["ai_probability"]

    # Generate code from the user's prompt using multiple models
    from prompt_engine import generate_multi_model_baselines
    baselines = await generate_multi_model_baselines(request.prompt, request.language)

    successful_comparisons = []
    
    for gen in baselines:
        if gen["status"] == "success" and gen["generated_code"]:
            similarity = await asyncio.to_thread(compute_similarity, request.code, gen["generated_code"])
            successful_comparisons.append({
                "model": gen["model_used"],
                "provider": gen.get("provider", "unknown"),
                "score": similarity["final_similarity"],
                "verdict": similarity["verdict"],
                "breakdown": similarity["breakdown"],
                "preview": gen["generated_code"][:200] + "..."
            })

    if successful_comparisons:
        # Use MAX similarity as the primary indicator
        max_similarity = max(c["score"] for c in successful_comparisons)
        avg_similarity = sum(c["score"] for c in successful_comparisons) / len(successful_comparisons)
        
        # If similarity is high, it heavily influences the result
        if max_similarity > 0.75:
            # Extremely high similarity to a known model output is near-certainty
            final_prob = (max_similarity * 0.8) + (base_prob * 0.2)
            confidence = 0.95
        elif max_similarity > 0.4:
            # Moderate similarity: check if multiple models show similar patterns
            consistency_bonus = 0.1 if len(successful_comparisons) > 1 and avg_similarity > 0.3 else 0
            final_prob = (max_similarity * 0.6) + (base_prob * 0.4) + consistency_bonus
            confidence = 0.75
        else:
            # Low similarity: trust the base analysis (NLP + Heuristics) more
            final_prob = (max_similarity * 0.3) + (base_prob * 0.7)
            confidence = base_analysis["details"].get("confidence_score", 0.5)
    else:
        max_similarity = 0
        final_prob = base_prob
        confidence = base_analysis["details"].get("confidence_score", 0.5)

    prompt_comparison = {
        "status": "success" if successful_comparisons else "failed",
        "models": successful_comparisons,
        "ensemble_count": len(successful_comparisons),
        "max_similarity": round(max_similarity, 3),
        "verdict": get_verdict(max_similarity) if successful_comparisons else "UNKNOWN",
    }

    base_analysis["ai_probability"] = round(max(0.0, min(1.0, final_prob)), 3)
    base_analysis["details"]["confidence_score"] = round(confidence, 2)
    base_analysis["prompt_comparison"] = prompt_comparison

    background_tasks.add_task(
        save_scan_to_db, 
        request.code, request.prompt, request.language, 
        base_analysis["ai_probability"], base_analysis["details"]
    )

    return base_analysis


@app.get("/ollama/status")
async def ollama_status():
    """Returns the current status of the local Ollama instance."""
    return check_ollama_status()


@app.get("/provider/status")
async def provider_status():
    """Returns the currently configured prompt engine provider and model."""
    return get_active_provider()


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
