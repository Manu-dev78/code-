"""
ML-based weighting system for combining heuristic and NLP scores.
Uses a simple feature-based approach to dynamically adjust weights based on code characteristics.
"""

def calculate_feature_weights(heuristic_details: dict, nlp_details: dict) -> dict:
    """
    Calculates dynamic weights for combining heuristic and NLP scores.
    Adjusts weights based on the confidence and characteristics of each analysis.
    """
    # Base weights
    weight_heuristic = 0.5
    weight_nlp = 0.5
    
    # Adjust based on NLP status
    nlp_status = nlp_details.get("status", "error")
    if nlp_status == "success":
        nlp_confidence = nlp_details.get("confidence", 0.5)
        # If NLP is confident, increase its weight
        if nlp_confidence > 0.8:
            weight_nlp = 0.7
            weight_heuristic = 0.3
        elif nlp_confidence < 0.6:
            # NLP is uncertain, trust heuristics more
            weight_nlp = 0.3
            weight_heuristic = 0.7
    elif nlp_status == "model_not_loaded":
        # No NLP available, use heuristics only
        weight_nlp = 0.0
        weight_heuristic = 1.0
    else:
        # NLP error, reduce its weight
        weight_nlp = 0.2
        weight_heuristic = 0.8
    
    # Adjust based on heuristic confidence
    artifact_score = heuristic_details.get("artifact_score", 0)
    if artifact_score > 0.5:
        # Strong AI artifacts detected, trust heuristics more
        weight_heuristic = min(0.9, weight_heuristic + 0.2)
        weight_nlp = max(0.1, weight_nlp - 0.2)
    
    # Normalize weights
    total = weight_heuristic + weight_nlp
    if total > 0:
        weight_heuristic /= total
        weight_nlp /= total
    
    return {
        "heuristic": round(weight_heuristic, 3),
        "nlp": round(weight_nlp, 3)
    }

def calculate_confidence_score(heuristic_prob: float, nlp_prob: float, weights: dict) -> float:
    """
    Calculates overall confidence based on agreement between methods.
    """
    # Agreement score: how close are the two probabilities?
    agreement = 1.0 - abs(heuristic_prob - nlp_prob)
    
    # Weight the agreement by the method weights
    confidence = (agreement * 0.7) + (max(weights["heuristic"], weights["nlp"]) * 0.3)
    
    return round(min(1.0, max(0.0, confidence)), 2)

def combine_scores(heuristic_result: dict, nlp_result: dict) -> dict:
    """
    Combines heuristic and NLP scores using dynamic weighting.
    Returns the combined result with confidence score.
    """
    h_prob = heuristic_result["ai_probability"]
    n_prob = nlp_result.get("nlp_ai_probability", 0.5)
    
    # Calculate dynamic weights
    weights = calculate_feature_weights(
        heuristic_result.get("details", {}),
        nlp_result
    )
    
    # Combine scores
    combined_prob = (h_prob * weights["heuristic"]) + (n_prob * weights["nlp"])
    
    # Calculate confidence
    confidence = calculate_confidence_score(h_prob, n_prob, weights)
    
    # Update result
    heuristic_result["ai_probability"] = round(combined_prob, 3)
    heuristic_result["details"]["confidence_score"] = confidence
    heuristic_result["details"]["weights_used"] = weights
    heuristic_result["details"]["nlp_status"] = nlp_result.get("status", "unknown")
    heuristic_result["details"]["nlp_score"] = n_prob
    
    return heuristic_result
