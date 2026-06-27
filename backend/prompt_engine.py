import os
import re
import httpx
from dotenv import load_dotenv

load_dotenv()

# --- Provider configuration ---
# Set PROMPT_ENGINE_PROVIDER in your .env file to one of:
#   "groq", "together", "huggingface", "ollama", "gemini", "sambanova", "cerebras"
PROVIDER = os.getenv("PROMPT_ENGINE_PROVIDER", "ollama").lower()

# API keys (only needed for cloud providers)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY", "")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")

# --- Provider-specific settings ---
PROVIDER_CONFIG = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "api_key_env": "GROQ_API_KEY",
    },
    "together": {
        "base_url": "https://api.together.xyz/v1/chat/completions",
        "model": os.getenv("TOGETHER_MODEL", "Qwen/Qwen2.5-Coder-7B-Instruct"),
        "api_key_env": "TOGETHER_API_KEY",
    },
    "huggingface": {
        "base_url": "https://api-inference.huggingface.co/models/{model}",
        "model": os.getenv("HF_MODEL", "Qwen/Qwen2.5-Coder-1.5B-Instruct"),
        "api_key_env": "HUGGINGFACE_API_KEY",
    },
    "sambanova": {
        "base_url": "https://api.sambanova.ai/v1/chat/completions",
        "model": os.getenv("SAMBANOVA_MODEL", "Meta-Llama-3.3-70B-Instruct"),
        "api_key_env": "SAMBANOVA_API_KEY",
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1/chat/completions",
        "model": os.getenv("CEREBRAS_MODEL", "llama3.1-70b"),
        "api_key_env": "CEREBRAS_API_KEY",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1/models/{model}:generateContent",
        "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        "api_key_env": "GEMINI_API_KEY",
    },
    "ollama": {
        "base_url": "http://localhost:11434",
        "preferred_models": ["qwen2.5-coder", "deepseek-coder", "codellama", "llama3", "llama2", "mistral"],
    },
}


def extract_code_from_response(text: str) -> str:
    """Strips markdown fences and prose, returning only the code block."""
    fence_pattern = re.compile(r"```(?:\w+)?\n?(.*?)```", re.DOTALL)
    matches = fence_pattern.findall(text)
    if matches:
        return max(matches, key=len).strip()
    return text.strip()


# ---------------------------------------------------------------------------
# Ollama helpers (local fallback)
# ---------------------------------------------------------------------------

def _check_ollama_status() -> dict:
    """Checks if Ollama is running and which models are available."""
    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
        if response.status_code == 200:
            data = response.json()
            available = [m["name"].split(":")[0] for m in data.get("models", [])]
            return {"running": True, "models": available}
        return {"running": False, "models": []}
    except (httpx.ConnectError, httpx.TimeoutException):
        return {"running": False, "models": []}


def _get_best_ollama_model(available: list[str]) -> str | None:
    preferred = PROVIDER_CONFIG["ollama"]["preferred_models"]
    for pref in preferred:
        for avail in available:
            if pref in avail.lower():
                return avail
    return available[0] if available else None


async def _generate_ollama(prompt: str, language: str) -> dict:
    status = _check_ollama_status()
    if not status["running"]:
        return {
            "status": "ollama_unavailable",
            "generated_code": None,
            "model_used": None,
            "error": "Ollama is not running. Set PROMPT_ENGINE_PROVIDER to 'groq', 'gemini', 'sambanova', etc., or start Ollama.",
        }

    model = _get_best_ollama_model(status["models"])
    if not model:
        return {
            "status": "no_models",
            "generated_code": None,
            "model_used": None,
            "error": "No Ollama models found. Run: ollama pull qwen2.5-coder:1.5b",
        }

    system_msg = (
        f"You are an expert {language} programmer. "
        "Generate ONLY the code requested — no explanations, no prose, no markdown. "
        "Output a single clean code block."
    )

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": model, "prompt": f"{system_msg}\n\nTask: {prompt}", "stream": False},
            )
        response.raise_for_status()
        raw = response.json().get("response", "")
        return {"status": "success", "generated_code": extract_code_from_response(raw), "model_used": model, "error": None}
    except httpx.TimeoutException:
        return {"status": "timeout", "generated_code": None, "model_used": model, "error": "Ollama timed out (>90s)."}
    except Exception as e:
        return {"status": "error", "generated_code": None, "model_used": model, "error": str(e)}


# ---------------------------------------------------------------------------
# OpenAI-compatible cloud providers (Groq, Together AI, SambaNova, Cerebras)
# ---------------------------------------------------------------------------

async def _generate_openai_compatible(prompt: str, language: str, provider: str) -> dict:
    config = PROVIDER_CONFIG[provider]
    api_key = os.getenv(config["api_key_env"], "")
    model = config["model"]

    if not api_key:
        return {
            "status": "missing_api_key",
            "generated_code": None,
            "model_used": model,
            "error": f"No API key found. Set {config['api_key_env']} in your .env file.",
        }

    system_msg = (
        f"You are an expert {language} programmer. "
        "Generate ONLY the code requested — no explanations, no prose, no markdown fences. "
        "Output raw code only."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(config["base_url"], json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        raw = data["choices"][0]["message"]["content"]
        return {
            "status": "success",
            "generated_code": extract_code_from_response(raw),
            "model_used": model,
            "provider": provider,
            "error": None,
        }
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:300] if e.response else str(e)
        return {"status": "api_error", "generated_code": None, "model_used": model, "error": detail}
    except httpx.TimeoutException:
        return {"status": "timeout", "generated_code": None, "model_used": model, "error": f"{provider} API timed out."}
    except Exception as e:
        return {"status": "error", "generated_code": None, "model_used": model, "error": str(e)}


# ---------------------------------------------------------------------------
# Google Gemini integration
# ---------------------------------------------------------------------------

async def _generate_gemini(prompt: str, language: str) -> dict:
    config = PROVIDER_CONFIG["gemini"]
    api_key = GEMINI_API_KEY
    model = config["model"]

    if not api_key:
        return {
            "status": "missing_api_key",
            "generated_code": None,
            "model_used": model,
            "error": "No API key found. Set GEMINI_API_KEY in your .env file.",
        }

    url = config["base_url"].format(model=model) + f"?key={api_key}"
    
    system_msg = (
        f"You are an expert {language} programmer. "
        "Generate ONLY the code requested — no explanations, no prose, no markdown fences. "
        "Output raw code only."
    )

    payload = {
        "contents": [{
            "parts": [{"text": f"{system_msg}\n\nTask: {prompt}"}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Extract text from Gemini response structure
        try:
            raw = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return {"status": "api_error", "generated_code": None, "model_used": model, "error": "Unexpected response format from Gemini"}

        return {
            "status": "success",
            "generated_code": extract_code_from_response(raw),
            "model_used": model,
            "provider": "gemini",
            "error": None,
        }
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:300] if e.response else str(e)
        return {"status": "api_error", "generated_code": None, "model_used": model, "error": detail}
    except Exception as e:
        return {"status": "error", "generated_code": None, "model_used": model, "error": str(e)}


# ---------------------------------------------------------------------------
# HuggingFace Inference API
# ---------------------------------------------------------------------------

async def _generate_huggingface(prompt: str, language: str) -> dict:
    api_key = HUGGINGFACE_API_KEY
    model = PROVIDER_CONFIG["huggingface"]["model"]

    if not api_key:
        return {
            "status": "missing_api_key",
            "generated_code": None,
            "model_used": model,
            "error": "No API key found. Set HUGGINGFACE_API_KEY in your .env file.",
        }

    system_msg = f"You are an expert {language} programmer. Output only raw code, no explanations."
    full_prompt = f"{system_msg}\n\nTask: {prompt}\n\nCode:"

    url = PROVIDER_CONFIG["huggingface"]["base_url"].format(model=model)
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "inputs": full_prompt,
        "parameters": {"max_new_tokens": 1024, "temperature": 0.2, "return_full_text": False},
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        raw = data[0]["generated_text"] if isinstance(data, list) else data.get("generated_text", "")
        return {
            "status": "success",
            "generated_code": extract_code_from_response(raw),
            "model_used": model,
            "provider": "huggingface",
            "error": None,
        }
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:300] if e.response else str(e)
        return {"status": "api_error", "generated_code": None, "model_used": model, "error": detail}
    except Exception as e:
        return {"status": "error", "generated_code": None, "model_used": model, "error": str(e)}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_available_providers() -> list[str]:
    """Returns a list of providers that have API keys configured, plus 'ollama'."""
    available = []
    for p, config in PROVIDER_CONFIG.items():
        if p == "ollama":
            if _check_ollama_status()["running"]:
                available.append(p)
        else:
            if os.getenv(config["api_key_env"]):
                available.append(p)
    return available


async def generate_code_from_prompt(prompt: str, language: str = "python", provider_override: str = None) -> dict:
    """
    Routes the code generation request to the configured provider.
    """
    active_provider = provider_override.lower() if provider_override else PROVIDER
    
    if active_provider in ("groq", "together", "sambanova", "cerebras"):
        return await _generate_openai_compatible(prompt, language, active_provider)
    elif active_provider == "gemini":
        return await _generate_gemini(prompt, language)
    elif active_provider == "huggingface":
        return await _generate_huggingface(prompt, language)
    else:
        # Default: local Ollama
        return await _generate_ollama(prompt, language)


async def generate_multi_model_baselines(prompt: str, language: str = "python", limit: int = 10) -> list[dict]:
    """
    Generates code baselines from multiple available providers in parallel.
    """
    providers = get_available_providers()
    # Prioritize cloud providers over local ollama for better accuracy if available
    if "ollama" in providers and len(providers) > 1:
        providers.remove("ollama")
        providers.append("ollama") # Put it at the end
    
    selected_providers = providers[:limit]
    tasks = [generate_code_from_prompt(prompt, language, p) for p in selected_providers]
    import asyncio
    results = await asyncio.gather(*tasks)
    return results


def check_ollama_status() -> dict:
    return _check_ollama_status()


def get_active_provider() -> dict:
    config = PROVIDER_CONFIG.get(PROVIDER, {})
    return {
        "provider": PROVIDER,
        "model": config.get("model", "auto-detected"),
        "available_providers": list(PROVIDER_CONFIG.keys())
    }
