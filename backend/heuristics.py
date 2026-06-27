import re
import ast
import math
from collections import Counter

def calculate_cyclomatic_complexity(node):
    """Calculates cyclomatic complexity of an AST node."""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.For, ast.While, ast.And, ast.Or, ast.ExceptHandler, ast.With)):
            complexity += 1
    return complexity

def calculate_entropy(text: str) -> float:
    """Calculates the Shannon entropy of the given text."""
    if not text:
        return 0.0
    probabilities = [text.count(c) / len(text) for c in set(text)]
    return -sum(p * math.log2(p) for p in probabilities)

def calculate_perplexity_score(code: str) -> float:
    """
    Measures how 'predictable' the code is using n-gram analysis.
    AI code tends to be more predictable (lower perplexity).
    Human code has more variation and unexpected patterns.
    Returns a score between 0 and 1 where higher = more AI-like.
    """
    lines = [l.strip() for l in code.split('\n') if l.strip() and not l.strip().startswith('#')]
    if len(lines) < 3:
        return 0.5
    
    # Extract token sequences
    tokens = re.findall(r'\b\w+\b|[^\s\w]', code)
    if len(tokens) < 5:
        return 0.5
    
    # Calculate bigram and trigram diversity
    bigrams = list(zip(tokens[:-1], tokens[1:]))
    trigrams = list(zip(tokens[:-2], tokens[1:-1], tokens[2:]))
    
    bigram_diversity = len(set(bigrams)) / len(bigrams) if bigrams else 0.5
    trigram_diversity = len(set(trigrams)) / len(trigrams) if trigrams else 0.5
    
    # AI code has lower diversity (more repetitive patterns)
    diversity_score = (bigram_diversity + trigram_diversity) / 2
    
    # Low diversity = high AI probability
    ai_prob = max(0.0, min(1.0, 1.0 - diversity_score))
    return round(ai_prob, 3)

def detect_error_handling(code: str, language: str) -> dict:
    """
    Analyzes error handling patterns.
    Human code typically has more defensive programming.
    AI code often lacks proper error handling or uses generic patterns.
    """
    lines = code.split('\n')
    code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
    total_lines = len(code_lines)
    
    if total_lines < 5:
        return {"error_handling_ratio": 0.5, "has_defensive_patterns": False}
    
    # Count error handling constructs
    error_patterns = [
        r'\btry\s*:',
        r'\bexcept\b',
        r'\bcatch\s*\(',
        r'\bif\s+.*\s+(is\s+None|==\s*None|!=\s*None)',
        r'\bif\s+not\s+\w+',
        r'\braise\b',
        r'\bthrow\b',
        r'\bassert\b',
        r'\bvalidate\b',
        r'\bcheck\b',
    ]
    
    error_count = 0
    for line in code_lines:
        for pattern in error_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                error_count += 1
                break
    
    error_ratio = error_count / total_lines
    
    # Humans typically have 5-15% error handling lines
    # AI code often has 0-3% or overly uniform distribution
    if 0.03 <= error_ratio <= 0.15:
        score = 0.3  # More human-like
    elif error_ratio < 0.03:
        score = 0.8  # Likely AI (no error handling)
    else:
        score = 0.5  # Could be either
    
    return {
        "error_handling_ratio": round(error_ratio, 3),
        "has_defensive_patterns": error_ratio > 0.05,
        "defensive_score": round(score, 3)
    }

def detect_import_bloat(code: str) -> dict:
    """
    Detects excessive or unnecessary imports.
    AI tends to over-import or use verbose import patterns.
    """
    lines = code.split('\n')
    
    import_lines = [l for l in lines if re.match(r'\s*(import|from)\s+', l)]
    total_lines = len([l for l in lines if l.strip()])
    
    if total_lines == 0:
        return {"import_ratio": 0.5, "is_bloated": False}
    
    import_ratio = len(import_lines) / total_lines
    
    # Check for common AI import patterns
    ai_patterns = [
        r'import\s+(sys|os|json|time|re|math|datetime|collections|itertools|functools)',
        r'from\s+\w+\s+import\s+\*',
        r'import\s+\w+\s+as\s+\w+',
    ]
    
    ai_import_count = 0
    for line in import_lines:
        for pattern in ai_patterns:
            if re.search(pattern, line):
                ai_import_count += 1
                break
    
    # AI code often has high import ratio or specific patterns
    if import_ratio > 0.2 or ai_import_count > 3:
        score = 0.8
    elif import_ratio > 0.1:
        score = 0.6
    else:
        score = 0.3
    
    return {
        "import_ratio": round(import_ratio, 3),
        "ai_import_count": ai_import_count,
        "is_bloated": import_ratio > 0.15,
        "import_score": round(score, 3)
    }

def analyze_variable_naming(code: str) -> dict:
    """
    Analyzes variable naming patterns.
    AI code tends to have very consistent, descriptive names.
    Human code has more variation, abbreviations, and inconsistencies.
    """
    # Extract variable names (simplified)
    var_names = re.findall(r'\b([a-z_][a-z0-9_]*)\b', code)
    
    # Filter out keywords and common short names
    keywords = {'if', 'else', 'for', 'while', 'return', 'def', 'class', 'import', 'from', 
                'try', 'except', 'with', 'as', 'in', 'not', 'and', 'or', 'is', 'None', 
                'True', 'False', 'print', 'len', 'range', 'int', 'str', 'float', 'list'}
    meaningful_vars = [v for v in var_names if v not in keywords and len(v) > 1]
    
    if len(meaningful_vars) < 3:
        return {"naming_consistency": 0.5, "avg_name_length": 0}
    
    # Calculate name length statistics
    lengths = [len(v) for v in meaningful_vars]
    avg_length = sum(lengths) / len(lengths)
    
    # Calculate length variance (AI has low variance, humans have high)
    variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    
    # AI names are typically 8-12 chars with low std_dev
    # Human names vary more: 3-15+ chars with higher std_dev
    if 7 <= avg_length <= 11 and std_dev < 2.5:
        consistency_score = 0.85  # Very AI-like
    elif avg_length < 6 or std_dev > 4:
        consistency_score = 0.3   # More human-like
    else:
        consistency_score = 0.5
    
    return {
        "avg_name_length": round(avg_length, 2),
        "name_std_dev": round(std_dev, 2),
        "naming_consistency": round(consistency_score, 3),
        "var_count": len(meaningful_vars)
    }

def analyze_code_density(code: str) -> dict:
    """
    Analyzes code density patterns.
    AI code often has uniform density (comments spread evenly).
    Human code has clusters of dense code followed by sparse sections.
    """
    lines = code.split('\n')
    if len(lines) < 5:
        return {"density_variance": 0.5, "is_uniform": False}
    
    # Calculate lines of code vs comments per 5-line window
    window_size = 5
    densities = []
    
    for i in range(0, len(lines), window_size):
        window = lines[i:i+window_size]
        code_lines = sum(1 for l in window if l.strip() and not l.strip().startswith('#'))
        densities.append(code_lines / len(window))
    
    if len(densities) < 2:
        return {"density_variance": 0.5, "is_uniform": False}
    
    # Calculate variance in density
    avg_density = sum(densities) / len(densities)
    variance = sum((d - avg_density) ** 2 for d in densities) / len(densities)
    
    # AI code has low density variance (uniform)
    # Human code has higher variance (clusters)
    if variance < 0.05:
        score = 0.8  # Very uniform = AI-like
    elif variance > 0.15:
        score = 0.3  # Variable = human-like
    else:
        score = 0.5
    
    return {
        "density_variance": round(variance, 3),
        "avg_density": round(avg_density, 3),
        "is_uniform": variance < 0.08,
        "density_score": round(score, 3)
    }

def get_halstead_metrics(code: str) -> dict:
    """
    Simplified Halstead metrics: Distinct operators and operands.
    AI code often has a higher 'volume' for simple tasks than human code.
    """
    operators = set(re.findall(r'[\+\-\*/%&|^~<>!=]=?|==|!=|<=|>=|\*\*|//|<<|>>', code))
    operands = set(re.findall(r'\b[a-zA-Z_]\w*\b|\b\d+\b', code))
    
    n1 = len(operators)
    n2 = len(operands)
    N1 = len(re.findall(r'[\+\-\*/%&|^~<>!=]=?|==|!=|<=|>=|\*\*|//|<<|>>', code))
    N2 = len(re.findall(r'\b[a-zA-Z_]\w*\b|\b\d+\b', code))
    
    vocabulary = n1 + n2
    length = N1 + N2
    volume = length * math.log2(vocabulary) if vocabulary > 0 else 0
    difficulty = (n1 / 2) * (N2 / n2) if n2 > 0 else 0
    
    return {
        "halstead_volume": round(volume, 2),
        "halstead_difficulty": round(difficulty, 2)
    }

def detect_ai_artifacts(code: str) -> float:
    """
    Checks for common AI-generated markers in comments or code structure.
    """
    artifacts = [
        r"Here is the (?:Python|code|implementation)",
        r"This script (?:demonstrates|performs|calculates)",
        r"Sure, I can (?:help|provide)",
        r"// This code was generated",
        r"# This code was generated",
        r"import (?:sys|os|json|time|re|math|datetime)\s+import", # Common multiple imports on one line
        r"def main\(\):", # Very common AI entry point
        r'if __name__ == "__main__":\s+main\(\)', # Very standard AI footer
    ]
    
    score = 0
    for pattern in artifacts:
        if re.search(pattern, code, re.IGNORECASE):
            score += 0.25
    
    return min(1.0, score)

def analyze_python_ast(code: str) -> dict:
    """Analyzes Python code using the built-in ast module."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"ast_supported": False, "error": "Syntax error"}
    
    # 1. Cyclomatic Complexity
    complexity = calculate_cyclomatic_complexity(tree)
    
    # 2. Structural counts
    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    
    # 3. Docstring presence (AI heavily favors comprehensive docstrings)
    docstrings_count = 0
    if ast.get_docstring(tree): docstrings_count += 1
    for f in functions:
        if ast.get_docstring(f): docstrings_count += 1
    for c in classes:
        if ast.get_docstring(c): docstrings_count += 1
        
    total_structures = len(functions) + len(classes) + 1 # +1 for module
    docstring_ratio = docstrings_count / total_structures if total_structures > 0 else 0
    
    # Average complexity per function
    avg_complexity = complexity / len(functions) if functions else complexity

    return {
        "ast_supported": True,
        "complexity": complexity,
        "avg_complexity": avg_complexity,
        "docstring_ratio": docstring_ratio,
        "num_imports": len(imports),
    }

def analyze_code(code: str, language: str) -> dict:
    """
    Advanced heuristic analyzer for AI code detection.
    """
    lines = code.split('\n')
    num_lines = len(lines)
    
    if num_lines < 3: # Too short to analyze reliably
        return {"ai_probability": 0.5, "details": {"reason": "Code too short"}}

    # --- 1. Text-based Heuristics ---
    comment_lines = [l for l in lines if l.strip().startswith('#') or l.strip().startswith('//')]
    comment_ratio = len(comment_lines) / num_lines if num_lines > 0 else 0
    
    if 0.1 <= comment_ratio <= 0.35:
        comment_score = 0.85 # Tighter AI sweet spot
    elif comment_ratio > 0.4:
        comment_score = 0.4
    else:
        comment_score = 0.2

    words = re.findall(r'\b[a-zA-Z_]\w*\b', code)
    if words:
        avg_word_length = sum(len(w) for w in words) / len(words)
        if 7 <= avg_word_length <= 11:
            word_score = 0.85
        elif avg_word_length > 12:
            word_score = 0.5 # Humans use very long names too
        else:
            word_score = 0.25
    else:
        avg_word_length = 0
        word_score = 0.5

    entropy = calculate_entropy(code)
    # AI code is usually "orderly", entropy often between 4.0 and 5.2
    entropy_score = 0.8 if 4.2 <= entropy <= 5.0 else 0.4
    
    halstead = get_halstead_metrics(code)
    # AI code for simple tasks often has a Volume between 500 and 3000
    halstead_score = 0.7 if 500 <= halstead["halstead_volume"] <= 4000 else 0.4
    
    artifact_score = detect_ai_artifacts(code)

    # --- NEW: Behavioral Heuristics ---
    error_analysis = detect_error_handling(code, language)
    import_analysis = detect_import_bloat(code)
    naming_analysis = analyze_variable_naming(code)
    density_analysis = analyze_code_density(code)
    perplexity_score = calculate_perplexity_score(code)

    details = {
        "comment_ratio": round(comment_ratio, 3),
        "avg_word_length": round(avg_word_length, 2),
        "entropy": round(entropy, 3),
        "halstead_volume": halstead["halstead_volume"],
        "artifact_score": artifact_score,
        "heuristic_score_comment": round(comment_score, 3),
        "heuristic_score_words": round(word_score, 3),
        # New behavioral metrics
        "error_handling_ratio": error_analysis["error_handling_ratio"],
        "defensive_score": error_analysis.get("defensive_score", 0.5),
        "import_ratio": import_analysis["import_ratio"],
        "import_score": import_analysis.get("import_score", 0.5),
        "naming_consistency": naming_analysis["naming_consistency"],
        "name_std_dev": naming_analysis.get("name_std_dev", 0),
        "density_variance": density_analysis["density_variance"],
        "density_score": density_analysis.get("density_score", 0.5),
        "perplexity_score": perplexity_score,
    }

    # Weighting text heuristics (reduced weight to accommodate new features)
    ai_prob_base = (
        (comment_score * 0.12) + 
        (word_score * 0.12) + 
        (entropy_score * 0.10) + 
        (halstead_score * 0.10) + 
        (artifact_score * 0.12) +
        # New behavioral features
        (error_analysis.get("defensive_score", 0.5) * 0.12) +
        (import_analysis.get("import_score", 0.5) * 0.10) +
        (naming_analysis["naming_consistency"] * 0.12) +
        (density_analysis.get("density_score", 0.5) * 0.05) +
        (perplexity_score * 0.05)
    )

    # --- 2. AST-based Heuristics (Python Only) ---
    if language.lower() in ['python', 'py']:
        ast_stats = analyze_python_ast(code)
        details.update(ast_stats)
        
        if ast_stats.get("ast_supported"):
            doc_score = 1.0 if ast_stats["docstring_ratio"] > 0.75 else (0.4 if ast_stats["docstring_ratio"] > 0.3 else 0.1)
            comp_score = 0.9 if 1.8 <= ast_stats["avg_complexity"] <= 3.2 else 0.3
            
            ast_prob = (doc_score * 0.6) + (comp_score * 0.4)
            # 50% Text/Behavioral, 50% AST for Python
            ai_prob_base = (ai_prob_base * 0.5) + (ast_prob * 0.5)

    ai_prob = max(0.0, min(1.0, ai_prob_base))

    return {
        "ai_probability": round(ai_prob, 3),
        "details": details
    }

