"""
Resume Matcher Service - Flask App Integration & Usage Guide

✅ Status: Fully Integrated and Tested
All tests passing (5/5):
- Service initialization ✓
- Single predictions ✓
- Batch predictions ✓
- Error handling ✓
- Flask app integration ✓

Model Loading:
- Automatically loaded when Flask app starts
- Cached in memory (singleton pattern)
- Available as: app.resume_matcher

Usage: See examples below
"""

# ============================================================================
# EXAMPLE 1: Simple Route - Predict Match
# ============================================================================

# Add this to your route file (e.g., app/blueprints/match.py)

# from flask import Blueprint, request, jsonify
# from app import create_app
#
# match_bp = Blueprint('match', __name__)
#
# @match_bp.route('/predict', methods=['POST'])
# def predict_match():
#     """
#     Predict resume-job match probability
#     
#     Request JSON:
#     {
#         "skills": "Python, Flask, Docker, Kubernetes",
#         "experience": "5 years as Backend Developer",
#         "education": "BS Computer Science",
#         "job_role": "Senior Python Developer"
#     }
#     
#     Response:
#     {
#         "success": true,
#         "match_probability": 0.5481,
#         "match_percentage": 54.81,
#         "match_quality": "Fair"
#     }
#     """
#     from flask import current_app
#     
#     try:
#         data = request.get_json()
#         
#         # Check if resume matcher is available
#         if not current_app.resume_matcher:
#             return jsonify({
#                 'success': False,
#                 'error': 'Service unavailable',
#                 'message': 'Resume matcher service not loaded'
#             }), 503
#         
#         # Get match probability
#         probability = current_app.resume_matcher.predict_resume_match(
#             skills=data.get('skills', ''),
#             experience=data.get('experience', ''),
#             education=data.get('education', ''),
#             job_role=data.get('job_role', '')
#         )
#         
#         # Convert to percentage
#         percentage = round(probability * 100, 2)
#         quality = classify_quality(probability)
#         
#         return jsonify({
#             'success': True,
#             'match_probability': probability,
#             'match_percentage': percentage,
#             'match_quality': quality
#         })
#     
#     except ValueError as e:
#         return jsonify({
#             'success': False,
#             'error': 'Invalid input',
#             'message': str(e)
#         }), 400
#     
#     except Exception as e:
#         return jsonify({
#             'success': False,
#             'error': 'Prediction failed',
#             'message': str(e)
#         }), 500
#
# def classify_quality(probability):
#     """Classify match quality based on probability."""
#     if probability >= 0.8:
#         return "Excellent"
#     elif probability >= 0.6:
#         return "Good"
#     elif probability >= 0.4:
#         return "Fair"
#     else:
#         return "Poor"


# ============================================================================
# EXAMPLE 2: Batch Processing - Rank Multiple Candidates
# ============================================================================

# from typing import List, Dict
# from flask import current_app
#
# def rank_candidates(candidates: List[Dict], job_description: Dict) -> List[Dict]:
#     """
#     Rank candidates by resume-job match score.
#     
#     Args:
#         candidates: List of candidate dicts with keys:
#                    - name: str
#                    - skills: str
#                    - experience: str
#                    - education: str
#         job_description: Job posting dict with keys:
#                         - job_role: str
#                         - skills: str (required skills)
#     
#     Returns:
#         List of candidates with match scores, sorted by score (highest first)
#     
#     Example:
#         candidates = [
#             {
#                 "name": "John Smith",
#                 "skills": "Python, Flask, Docker",
#                 "experience": "5 years as Backend Developer",
#                 "education": "BS Computer Science"
#             },
#             {
#                 "name": "Jane Doe",
#                 "skills": "Java, Spring Boot, Kubernetes",
#                 "experience": "6 years as Backend Developer",
#                 "education": "MS Computer Science"
#             }
#         ]
#         
#         job = {
#             "job_role": "Senior Python Developer",
#             "skills": "Python, Docker, Kubernetes"
#         }
#         
#         ranked = rank_candidates(candidates, job)
#         # Returns candidates sorted by match probability (highest first)
#     """
#     if not current_app.resume_matcher:
#         raise RuntimeError("Resume matcher service not available")
#     
#     results = []
#     
#     for candidate in candidates:
#         try:
#             probability = current_app.resume_matcher.predict_resume_match(
#                 skills=candidate.get('skills', ''),
#                 experience=candidate.get('experience', ''),
#                 education=candidate.get('education', ''),
#                 job_role=job.get('job_role', '')
#             )
#             
#             results.append({
#                 'name': candidate['name'],
#                 'match_probability': probability,
#                 'match_percentage': round(probability * 100, 2),
#                 'match_quality': classify_quality(probability),
#                 'status': 'success'
#             })
#         except Exception as e:
#             results.append({
#                 'name': candidate['name'],
#                 'status': 'failed',
#                 'error': str(e),
#                 'match_probability': None,
#                 'match_percentage': None
#             })
#     
#     # Sort by match probability (highest first)
#     return sorted(
#         results,
#         key=lambda x: x.get('match_probability', 0),
#         reverse=True
#     )


# ============================================================================
# EXAMPLE 3: Filter Candidates - Find Only Good Matches
# ============================================================================

# def filter_qualified_candidates(
#     candidates: List[Dict],
#     job_description: Dict,
#     threshold: float = 0.6
# ) -> List[Dict]:
#     """
#     Filter candidates that meet minimum match threshold.
#     
#     Args:
#         candidates: List of candidate dicts
#         job_description: Job posting dict
#         threshold: Minimum match probability (0.0-1.0), default 0.6 (60%)
#     
#     Returns:
#         List of candidates meeting or exceeding threshold, sorted by score
#         
#     Example:
#         # Only return candidates with 60%+ match
#         qualified = filter_qualified_candidates(
#             candidates,
#             job,
#             threshold=0.6
#         )
#     """
#     ranked = rank_candidates(candidates, job_description)
#     
#     qualified = [
#         c for c in ranked
#         if c['status'] == 'success' and c['match_probability'] >= threshold
#     ]
#     
#     return qualified


# ============================================================================
# EXAMPLE 4: Test Standalone (No Flask Context)
# ============================================================================

# from app.services.resume_matcher_service import ResumeMatcherService
#
# # Direct service usage without Flask
# matcher = ResumeMatcherService(models_dir='models')
#
# probability = matcher.predict_resume_match(
#     skills="Python, Flask, Docker, Kubernetes, PostgreSQL, AWS",
#     experience="5 years experience as Backend Developer",
#     education="BS Computer Science",
#     job_role="Senior Python Developer"
# )
#
# print(f"Match Probability: {probability:.4f} ({probability*100:.2f}%)")


# ============================================================================
# FEATURE DETAILS
# ============================================================================

"""
Input Parameters:
-----------------
skills: str
    - Candidate's technical skills
    - Format: comma-separated or paragraph text
    - Example: "Python, Flask, Docker, Kubernetes"
    - Example: "Proficient in Python and Docker for containerized deployments"

experience: str
    - Candidate's professional work experience
    - Format: free text describing roles and years
    - Example: "5 years as Backend Developer at TechCorp"
    - Example: "Senior software engineer with expertise in microservices"

education: str
    - Candidate's educational background
    - Format: degree and institution
    - Example: "BS Computer Science from State University"
    - Example: "MS Data Science, MBA"

job_role: str
    - Target job position or role title
    - Format: job title or role description
    - Example: "Senior Python Developer"
    - Example: "Backend Engineer with Python and Docker expertise"

Return Values:
--------------
float (0.0 to 1.0)
    - 0.0 = very poor match (unlikely to succeed)
    - 0.5 = fair match (moderate fit)
    - 1.0 = perfect match (excellent fit)

Convert to percentage:
    percentage = probability * 100  # Result: 0-100%

Error Handling:
---------------
ValueError
    - Raised when all input parameters are empty
    - Raised when combined text produces no meaningful content
    - Message: "At least one of (skills, experience, education, job_role) required"

RuntimeError
    - Raised when model prediction fails
    - Indicates internal model or pipeline error
    - Message: "Prediction failed: ..."
"""


# ============================================================================
# QUALITY CLASSIFICATION HELPER
# ============================================================================

def classify_quality(probability: float) -> str:
    """
    Classify match quality based on probability score.
    
    Args:
        probability: Match probability (0.0 to 1.0)
    
    Returns:
        Quality classification string
        
    Ranges:
        0.80-1.00 -> "Excellent" (strong candidate)
        0.60-0.79 -> "Good"      (good candidate)
        0.40-0.59 -> "Fair"      (moderate fit)
        0.00-0.39 -> "Poor"      (weak match)
    """
    if probability >= 0.8:
        return "Excellent"
    elif probability >= 0.6:
        return "Good"
    elif probability >= 0.4:
        return "Fair"
    else:
        return "Poor"


# ============================================================================
# MODEL METADATA
# ============================================================================

"""
Model Architecture:
-------------------
1. TF-IDF Vectorizer
   - Converts text to numerical features
   - Vocab size: 47 unique tokens (from training data)

2. Truncated SVD (46 components)
   - Dimensionality reduction
   - Captures latent semantic features
   - Note: Auto-adjusted from 100 to 46 based on vocabulary

3. Standard Scaler
   - Normalizes features to zero mean, unit variance
   - Ensures SVM receives properly scaled input

4. SVM Classifier
   - Kernel: RBF (Radial Basis Function)
   - Probability: Enabled
   - Random state: 42 (reproducible)
   - Solves binary classification: 0 (poor match) vs 1 (good match)

Training Data:
   - Dataset: resume_training_dataset_600.csv
   - Samples: 600 resumes
   - Split: 80% train, 20% test
   - Features: skills + work_experience + education + job_role (combined text)
   - Target: Binary label (0 or 1)

Performance Metrics:
   - Accuracy: 0.4333 (note: dataset imbalance)
   - Precision: 0.3654
   - Recall: 0.3519
   - F1-Score: 0.3585

Note: Low metrics suggest the model needs more/better labeled training data
      for production use. Current model is suitable for demonstration/testing.
"""


# ============================================================================
# PRODUCTION BEST PRACTICES
# ============================================================================

"""
✓ Do:
  - Check app.resume_matcher is not None before using
  - Handle ValueError and RuntimeError exceptions
  - Use meaningful error messages in API responses
  - Log prediction errors for debugging
  - Validate input length before sending to model
  - Cache expensive computations (batch operations)
  - Monitor model predictions for anomalies
  - Periodically retrain with new labeled data

✗ Don't:
  - Assume resume_matcher is always available
  - Ignore exceptions and assume predictions succeed
  - Send extremely long text (>100KB) to model
  - Retrain/replace model during runtime
  - Use probability > 1.0 or < 0.0 (shouldn't happen)
  - Trust model predictions from untrained data
"""
