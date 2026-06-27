try:
    from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    pipeline = None

if TRANSFORMERS_AVAILABLE:
    print("Loading NLP Model...")
    try:
        # Use a code-specific model for better AI detection
        # CodeBERT is trained on code and can detect AI patterns better
        pipe = pipeline(
            "text-classification", 
            model="microsoft/codebert-base",
            tokenizer="microsoft/codebert-base",
            device=-1,
            framework="pt"
        )
        print("NLP Model loaded successfully.")
    except Exception as e:
        print(f"Failed to load NLP Model: {e}")
        pipe = None
else:
    print("Transformers not available. NLP analysis will be skipped.")
    pipe = None

def analyze_code_perplexity(code: str) -> float:
    """
    Analyzes code perplexity using n-gram language modeling.
    AI-generated code tends to have lower perplexity (more predictable).
    Human code has higher perplexity (more variation, unexpected patterns).
    
    Returns a score between 0 and 1 where higher = more AI-like.
    """
    lines = [l.strip() for l in code.split('\n') if l.strip() and not l.strip().startswith('#')]
    if len(lines) < 3:
        return 0.5
    
    # Extract token sequences
    import re
    tokens = re.findall(r'\b\w+\b|[^\s\w]', code)
    if len(tokens) < 10:
        return 0.5
    
    # Calculate trigram perplexity
    trigrams = list(zip(tokens[:-2], tokens[1:-1], tokens[2:]))
    if not trigrams:
        return 0.5
    
    # Count trigram frequencies
    trigram_counts = {}
    for tri in trigrams:
        trigram_counts[tri] = trigram_counts.get(tri, 0) + 1
    
    # Calculate average probability
    total_trigrams = len(trigrams)
    unique_trigrams = len(trigram_counts)
    
    # Perplexity score: AI code has fewer unique trigrams relative to total
    uniqueness_ratio = unique_trigrams / total_trigrams
    
    # Lower uniqueness = more predictable = more AI-like
    ai_prob = max(0.0, min(1.0, 1.0 - uniqueness_ratio))
    return round(ai_prob, 3)

def analyze_code_structure(code: str) -> dict:
    """
    Analyzes code structure patterns that differentiate AI from human code.
    """
    import re
    
    lines = code.split('\n')
    code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
    
    if len(code_lines) < 3:
        return {"structure_score": 0.5, "patterns": []}
    
    patterns_detected = []
    
    # Check for AI-typical patterns
    ai_patterns = {
        "excessive_docstrings": len(re.findall(r'""".*?"""', code, re.DOTALL)) > 2,
        "uniform_indentation": all(len(l) - len(l.lstrip()) == len(code_lines[0]) - len(code_lines[0].lstrip()) for l in code_lines if l.strip()),
        "boilerplate_main": bool(re.search(r'if\s+__name__\s*==\s*["\']__main__["\']:', code)),
        "type_hints_everywhere": len(re.findall(r':\s*(str|int|float|bool|list|dict|Optional|Union)', code)) > 3,
        "perfect_naming": all(re.match(r'^[a-z_][a-z0-9_]*$', l.split('=')[0].strip()) for l in code_lines if '=' in l and not l.strip().startswith('#')),
    }
    
    ai_pattern_count = sum(ai_patterns.values())
    patterns_detected = [k for k, v in ai_patterns.items() if v]
    
    # More AI patterns detected = higher AI probability
    structure_score = min(1.0, ai_pattern_count / 3.0)
    
    return {
        "structure_score": round(structure_score, 3),
        "patterns": patterns_detected,
        "ai_pattern_count": ai_pattern_count
    }

def analyze_with_nlp(code: str) -> dict:
    """
    Analyzes code using an NLP pipeline and structural analysis to determine AI probability.
    Returns a dictionary with the score.
    """
    # Always run structural analysis (doesn't require model)
    structure_result = analyze_code_structure(code)
    perplexity_score = analyze_code_perplexity(code)
    
    # Combine structural and perplexity scores
    structural_ai_prob = (structure_result["structure_score"] * 0.6) + (perplexity_score * 0.4)
    
    if pipe is None:
        return {
            "nlp_ai_probability": structural_ai_prob,
            "status": "model_not_loaded",
            "structural_score": structure_result["structure_score"],
            "perplexity_score": perplexity_score,
            "patterns": structure_result["patterns"]
        }
        
    try:
        # CodeBERT has a max sequence length of 512 tokens.
        truncated_code = code[:1500] 
        
        result = pipe(truncated_code)
        
        prediction = result[0]
        label = prediction['label'].lower()
        score = prediction['score']
        
        # CodeBERT returns different labels than RoBERTa
        if label in ['fake', 'ai', 'label_1', 'human']:
            # Adjust based on label semantics
            if label == 'human':
                ai_prob = 1.0 - score
            else:
                ai_prob = score
        else:
            ai_prob = 1.0 - score
            
        # Combine model prediction with structural analysis
        # Weight model less if it's uncertain, structural more if patterns are clear
        model_confidence = abs(ai_prob - 0.5) * 2  # 0 = uncertain, 1 = confident
        
        if model_confidence > 0.7:
            # Model is confident, trust it more
            final_prob = (ai_prob * 0.6) + (structural_ai_prob * 0.4)
        else:
            # Model is uncertain, trust structural analysis more
            final_prob = (ai_prob * 0.3) + (structural_ai_prob * 0.7)
            
        return {
            "nlp_ai_probability": round(final_prob, 3),
            "status": "success",
            "raw_label": label,
            "confidence": round(score, 3),
            "structural_score": structure_result["structure_score"],
            "perplexity_score": perplexity_score,
            "patterns": structure_result["patterns"]
        }
    except Exception as e:
        print(f"Error during NLP inference: {e}")
        return {
            "nlp_ai_probability": structural_ai_prob,
            "status": "error",
            "error_msg": str(e),
            "structural_score": structure_result["structure_score"],
            "perplexity_score": perplexity_score,
            "patterns": structure_result["patterns"]
        }
