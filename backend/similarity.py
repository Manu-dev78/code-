import ast
import difflib
import re
import tokenize
import io
from typing import Optional, List

# Attempt to load sentence-transformers for semantic similarity (optional)
try:
    from sentence_transformers import SentenceTransformer, util
    _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    EMBEDDINGS_AVAILABLE = True
    print("Sentence-transformers loaded for semantic similarity.")
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    _embed_model = None
    print("sentence-transformers not installed. Semantic similarity will be skipped.")


def tokenize_code(code: str) -> List[str]:
    """
    Robustly tokenizes code, stripping comments and docstrings.
    Works best for Python but falls back to regex for other languages.
    """
    try:
        tokens = []
        # Try Python tokenizer
        for tok in tokenize.generate_tokens(io.StringIO(code).readline):
            if tok.type in (tokenize.COMMENT, tokenize.NL, tokenize.INDENT, tokenize.DEDENT):
                continue
            # Also skip docstrings (strings that are their own expression)
            if tok.type == tokenize.STRING and len(tokens) > 0 and tokens[-1] == "def":
                continue # Simple heuristic for docstrings in function defs
            tokens.append(tok.string.strip())
        return [t for t in tokens if t]
    except Exception:
        # Regex fallback for other languages or broken code
        # Remove comments first
        code = re.sub(r'#.*|//.*|/\*.*?\*/', '', code, flags=re.DOTALL)
        return re.findall(r'\b\w+\b|[^\s\w]', code)


def get_ngrams(tokens: List[str], n: int = 3) -> set:
    """Generates N-grams from tokens."""
    return set(zip(*[tokens[i:] for i in range(n)]))


def jaccard_similarity(ngrams_a: set, ngrams_b: set) -> float:
    """Computes Jaccard similarity between two sets of N-grams."""
    if not ngrams_a or not ngrams_b:
        return 0.0
    intersection = len(ngrams_a & ngrams_b)
    union = len(ngrams_a | ngrams_b)
    return intersection / union


def lcs_similarity(tokens_a: List[str], tokens_b: List[str]) -> float:
    """Computes Longest Common Subsequence similarity ratio."""
    if not tokens_a or not tokens_b:
        return 0.0
    matcher = difflib.SequenceMatcher(None, tokens_a, tokens_b)
    return matcher.ratio()


def get_ast_profile(code: str) -> Optional[dict]:
    """Parses code into an AST and extracts a structural 'profile'."""
    try:
        tree = ast.parse(code)
    except Exception:
        return None

    profile = {}
    for node in ast.walk(tree):
        node_type = type(node).__name__
        profile[node_type] = profile.get(node_type, 0) + 1
    return profile


def ast_structural_similarity(code_a: str, code_b: str) -> float:
    """Compares AST node-type profiles."""
    profile_a = get_ast_profile(code_a)
    profile_b = get_ast_profile(code_b)

    if profile_a is None or profile_b is None:
        return 0.0

    all_keys = set(profile_a.keys()) | set(profile_b.keys())
    if not all_keys:
        return 0.0

    dot_product = sum(profile_a.get(k, 0) * profile_b.get(k, 0) for k in all_keys)
    magnitude_a = sum(v ** 2 for v in profile_a.values()) ** 0.5
    magnitude_b = sum(v ** 2 for v in profile_b.values()) ** 0.5

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return round(dot_product / (magnitude_a * magnitude_b), 4)


def semantic_similarity(code_a: str, code_b: str) -> Optional[float]:
    """Computes semantic embedding similarity."""
    if not EMBEDDINGS_AVAILABLE or _embed_model is None:
        return None

    try:
        emb_a = _embed_model.encode(code_a, convert_to_tensor=True)
        emb_b = _embed_model.encode(code_b, convert_to_tensor=True)
        score = util.cos_sim(emb_a, emb_b).item()
        return round(max(0.0, score), 4)
    except Exception:
        return None


def get_verdict(score: float) -> str:
    """Maps a similarity score to a human-readable verdict."""
    if score >= 0.80:
        return "HIGH_MATCH"
    elif score >= 0.50:
        return "MODERATE_MATCH"
    elif score >= 0.25:
        return "LOW_MATCH"
    else:
        return "NO_MATCH"


def get_structural_hash(code: str) -> List[str]:
    """
    Creates a structural representation of the code by replacing all 
    user-defined identifiers and literals with placeholders.
    This makes the similarity check robust against renaming.
    """
    try:
        tokens = []
        for tok in tokenize.generate_tokens(io.StringIO(code).readline):
            if tok.type == tokenize.NAME:
                # Distinguish between keywords and identifiers
                import keyword
                if keyword.iskeyword(tok.string):
                    tokens.append(tok.string)
                else:
                    tokens.append("ID")
            elif tok.type == tokenize.STRING:
                tokens.append("STR")
            elif tok.type == tokenize.NUMBER:
                tokens.append("NUM")
            elif tok.type in (tokenize.OP, tokenize.NEWLINE):
                tokens.append(tok.string)
        return [t for t in tokens if t.strip()]
    except Exception:
        # Regex fallback: replace names and numbers
        code = re.sub(r'\b[a-zA-Z_]\w*\b', 'ID', code)
        code = re.sub(r'\b\d+\b', 'NUM', code)
        code = re.sub(r'".*?"|\'.*?\'', 'STR', code)
        return re.findall(r'ID|NUM|STR|[^\s\w]', code)

def compute_similarity(user_code: str, generated_code: str) -> dict:
    """
    Advanced multi-layer similarity detection.
    """
    tokens_u = tokenize_code(user_code)
    tokens_g = tokenize_code(generated_code)

    # 1. Token Overlap (LCS & Jaccard) - Direct string comparison
    lcs_score = lcs_similarity(tokens_u, tokens_g)
    j_score = jaccard_similarity(get_ngrams(tokens_u), get_ngrams(tokens_g))
    token_final = (lcs_score * 0.7) + (j_score * 0.3)

    # 2. Structural Hashing - Logic pattern comparison (ignores naming)
    struct_u = get_structural_hash(user_code)
    struct_g = get_structural_hash(generated_code)
    struct_lcs = lcs_similarity(struct_u, struct_g)
    struct_j = jaccard_similarity(get_ngrams(struct_u), get_ngrams(struct_g))
    struct_final = (struct_lcs * 0.7) + (struct_j * 0.3)

    # 3. AST Profile (Node type distribution)
    ast_score = ast_structural_similarity(user_code, generated_code)

    # 4. Semantic Embedding
    sem_score = semantic_similarity(user_code, generated_code)

    # Scoring logic:
    # If structural similarity is much higher than token similarity, 
    # it's a strong sign of "humanized" AI code (names changed).
    
    if sem_score is not None:
        # 20% Token, 40% Structural, 20% AST, 20% Semantic
        final_score = (token_final * 0.2) + (struct_final * 0.4) + (ast_score * 0.2) + (sem_score * 0.2)
        method = "hybrid (token + structural + ast + semantic)"
    else:
        # 30% Token, 50% Structural, 20% AST
        final_score = (token_final * 0.3) + (struct_final * 0.5) + (ast_score * 0.2)
        method = "hybrid (token + structural + ast)"

    # Boost if structural is significantly higher than token (evidence of obfuscation)
    if struct_final > token_final + 0.3:
        final_score = min(1.0, final_score + 0.15)

    final_score = round(max(0.0, min(1.0, final_score)), 4)

    return {
        "final_similarity": final_score,
        "verdict": get_verdict(final_score),
        "breakdown": {
            "token_similarity": round(token_final, 4),
            "structural_similarity": round(struct_final, 4),
            "ast_similarity": round(ast_score, 4),
            "semantic_similarity": sem_score,
        },
        "method": method,
    }

