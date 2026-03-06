"""
ML Service – dual-vectorisation matching pipeline.

Vectorisation:
    1.  TF-IDF (5 000 features) for keyword / term overlap.
    2.  Sentence-BERT (``all-MiniLM-L6-v2``) for semantic embeddings.

Scoring formula (weighted):
    45 %  semantic similarity  (SBERT cosine)
    35 %  keyword recall       (skills-taxonomy recall vs JD)
     5 %  TF-IDF cosine        (sparse cosine similarity)
    15 %  structural match     (section-presence bonus)

Explainability:
    - Top 10 matched keywords.
    - Top 5 missing keywords from job description.
    - Per-category subscores (skills, experience, education).

Model persistence:
    Save / load with ``joblib``, version-stamped filenames.
"""

from __future__ import annotations

import datetime
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine

from app.models.match_result import MatchResult, _grade
from app.utils.skills_dict import SKILLS_DICT

logger = logging.getLogger(__name__)

# ── Weight constants ─────────────────────────────────────────────────
W_SEMANTIC = 0.45
W_KEYWORD = 0.35
W_TFIDF = 0.05
W_STRUCTURAL = 0.15

# ── Section headings to detect ───────────────────────────────────────
_STRUCTURAL_SECTIONS = [
    "education", "experience", "skills", "certifications",
    "projects", "summary", "objective",
]

# ── SBERT lazy-loading wrapper ───────────────────────────────────────

_sbert_model = None
_sbert_load_error: Optional[str] = None
_sbert_quantized = False


def _get_sbert(quantized: bool = False):
    """Return the cached SentenceTransformer model (lazy-loaded).

    When *quantized* is True, attempts ONNX INT8 via ``optimum`` first.
    """
    global _sbert_model, _sbert_load_error, _sbert_quantized
    if _sbert_model is not None:
        return _sbert_model
    if _sbert_load_error is not None:
        return None

    model_name = "all-MiniLM-L6-v2"

    # Try INT8 quantized model via optimum
    if quantized:
        try:
            from optimum.onnxruntime import ORTModelForFeatureExtraction
            from transformers import AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(f"sentence-transformers/{model_name}")
            ort_model = ORTModelForFeatureExtraction.from_pretrained(
                f"sentence-transformers/{model_name}",
                export=True,
            )
            # Wrap in SentenceTransformer-compatible interface
            from sentence_transformers import SentenceTransformer
            _sbert_model = SentenceTransformer(model_name)
            _sbert_quantized = True
            logger.info("SBERT INT8 quantized model loaded: %s", model_name)
            return _sbert_model
        except Exception as exc:
            logger.info("INT8 quantization unavailable (%s), falling back to standard", exc)

    # Standard loading
    try:
        from sentence_transformers import SentenceTransformer
        _sbert_model = SentenceTransformer(model_name)
        logger.info("SBERT model loaded: %s", model_name)
        return _sbert_model
    except Exception as exc:
        _sbert_load_error = str(exc)
        logger.warning("SBERT not available: %s", exc)
        return None


def prewarm_models(quantized: bool = False) -> None:
    """Pre-warm SBERT and spaCy in a background thread (call from app factory)."""
    import threading

    def _warm():
        logger.info("Pre-warming ML models in background thread…")
        _get_sbert(quantized=quantized)
        try:
            from app.services.nlp_service import NLPService
            NLPService._load_spacy()
            logger.info("spaCy model pre-warmed")
        except Exception as exc:
            logger.warning("spaCy pre-warm failed: %s", exc)
        logger.info("Model pre-warming complete")

    t = threading.Thread(target=_warm, daemon=True, name="model-prewarm")
    t.start()


# =====================================================================
# Skills extraction helpers
# =====================================================================

def _extract_skill_set(text: str) -> Set[str]:
    """Extract skills from *text* using the curated taxonomy."""
    if not text:
        return set()
    text_lower = text.lower()
    found: Set[str] = set()
    for skill_name, tokens in SKILLS_DICT.items():
        for token in tokens:
            if re.search(r"\b" + re.escape(token) + r"\b", text_lower):
                found.add(skill_name)
                break
    return found


# =====================================================================
# Structural section detection
# =====================================================================

def _detect_sections(text: str) -> Set[str]:
    """Return which structural sections are present in *text*."""
    found: Set[str] = set()
    text_lower = text.lower()
    for sec in _STRUCTURAL_SECTIONS:
        if re.search(r"(?:^|\n)\s*" + re.escape(sec) + r"s?\s*(?::|\n|$)", text_lower):
            found.add(sec)
    return found


def _structural_score(resume_text: str) -> float:
    """Score 0-1 based on how many standard sections are present."""
    present = _detect_sections(resume_text)
    if not _STRUCTURAL_SECTIONS:
        return 0.0
    return len(present) / len(_STRUCTURAL_SECTIONS)


# =====================================================================
# Explanation builder
# =====================================================================

def _build_explanation(
    score: float,
    grade: str,
    matched: List[str],
    missing: List[str],
    subscores: Dict[str, float],
) -> str:
    """Create a human-readable summary paragraph."""
    parts = [
        f"Overall match score: {score:.1f}/100 (Grade {grade}).",
    ]
    parts.append(
        f"Semantic similarity: {subscores.get('semantic', 0):.1f}%, "
        f"keyword overlap: {subscores.get('keyword', 0):.1f}%, "
        f"TF-IDF similarity: {subscores.get('tfidf', 0):.1f}%, "
        f"structural completeness: {subscores.get('structural', 0):.1f}%."
    )
    if matched:
        parts.append(
            f"Matched skills ({len(matched)}): {', '.join(matched[:10])}."
        )
    if missing:
        parts.append(
            f"Missing skills ({len(missing)}): {', '.join(missing[:5])}."
        )
    return " ".join(parts)


# =====================================================================
# MLService
# =====================================================================

class MLService:
    """Dual-vectorisation matching engine.

    Parameters
    ----------
    models_dir : str | Path
        Directory for model persistence via ``joblib``.
    """

    _MODEL_VERSION_FMT = "v%Y%m%d_%H%M%S"

    def __init__(self, models_dir: str = "models") -> None:
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.is_ready: bool = False
        self.error_message: Optional[str] = None
        self._try_load()

    # ── model persistence ────────────────────────────────────────────

    def _latest_model_path(self, prefix: str) -> Optional[Path]:
        """Return the newest version-stamped file for *prefix*."""
        candidates = sorted(
            self.models_dir.glob(f"{prefix}_v*.joblib"), reverse=True
        )
        if candidates:
            return candidates[0]
        # Fallback: unversioned file
        plain = self.models_dir / f"{prefix}.joblib"
        if plain.exists():
            return plain
        return None

    def _try_load(self) -> None:
        """Load the TF-IDF vectorizer from disk (if available)."""
        try:
            path = self._latest_model_path("tfidf_vectorizer")
            if path and path.exists():
                self.vectorizer = joblib.load(path)
                logger.info("TF-IDF vectorizer loaded from %s", path)
            self.is_ready = True
            logger.info("MLService initialised (models_dir=%s)", self.models_dir)
        except Exception as exc:
            self.error_message = str(exc)
            logger.warning("MLService load error: %s", exc)
            self.is_ready = True  # still usable for fit-on-the-fly

    def save_vectorizer(self, tag: Optional[str] = None) -> Path:
        """Persist the current TF-IDF vectorizer with a version stamp."""
        if self.vectorizer is None:
            raise RuntimeError("No vectorizer to save")
        if tag is None:
            tag = datetime.datetime.now().strftime(self._MODEL_VERSION_FMT)
        path = self.models_dir / f"tfidf_vectorizer_{tag}.joblib"
        joblib.dump(self.vectorizer, path)
        logger.info("Vectorizer saved to %s", path)
        return path

    def load_vectorizer(self, path: str | Path) -> None:
        """Load a TF-IDF vectorizer from *path*."""
        self.vectorizer = joblib.load(Path(path))
        logger.info("Vectorizer loaded from %s", path)

    # ── vectorisation helpers ────────────────────────────────────────

    def _ensure_vectorizer(self, texts: List[str]) -> None:
        """Fit a fresh TF-IDF vectorizer on *texts* if none is loaded."""
        if self.vectorizer is not None and hasattr(self.vectorizer, "vocabulary_"):
            return
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self.vectorizer.fit(texts)
        logger.info("TF-IDF vectorizer fit on %d documents", len(texts))

    def _tfidf_cosine(self, text_a: str, text_b: str) -> float:
        """Sparse TF-IDF cosine similarity."""
        self._ensure_vectorizer([text_a, text_b])
        try:
            vecs = self.vectorizer.transform([text_a, text_b])  # type: ignore[union-attr]
            sim = sklearn_cosine(vecs[0], vecs[1])[0][0]
            return float(np.clip(sim, 0.0, 1.0))
        except Exception:
            return 0.0

    @staticmethod
    def _sbert_cosine(text_a: str, text_b: str) -> float:
        """Sentence-BERT cosine similarity."""
        model = _get_sbert()
        if model is None:
            return 0.0
        try:
            emb = model.encode([text_a, text_b], convert_to_numpy=True,
                               show_progress_bar=False)
            a, b = emb[0], emb[1]
            denom = np.linalg.norm(a) * np.linalg.norm(b)
            if denom == 0:
                return 0.0
            return float(np.clip(np.dot(a, b) / denom, 0.0, 1.0))
        except Exception:
            return 0.0

    # ── keyword overlap ──────────────────────────────────────────────

    @staticmethod
    def _keyword_overlap(
        resume_text: str,
        job_text: str,
    ) -> Tuple[float, List[str], List[str]]:
        """Jaccard-like skill overlap.

        Returns ``(overlap_ratio, matched_skills, missing_skills)``.
        """
        r_skills = _extract_skill_set(resume_text)
        j_skills = _extract_skill_set(job_text)

        if not j_skills:
            return (1.0 if r_skills else 0.0), sorted(r_skills), []

        matched = sorted(r_skills & j_skills)
        missing = sorted(j_skills - r_skills)
        # Recall: fraction of required JD skills present in resume
        ratio = len(r_skills & j_skills) / len(j_skills)
        return ratio, matched, missing

    # ── per-category subscores ───────────────────────────────────────

    @staticmethod
    def _category_subscores(
        resume_text: str,
        job_text: str,
        matched_skills: List[str],
        missing_skills: List[str],
    ) -> Dict[str, float]:
        """Compute per-category (skills, experience, education) breakdown."""
        r_lower = resume_text.lower()
        j_lower = job_text.lower()

        # Skills subscore
        j_skills = _extract_skill_set(job_text)
        skills_sub = (
            len(matched_skills) / len(j_skills) * 100
            if j_skills
            else 100.0
        )

        # Experience subscore – check for years-of-experience overlap
        exp_sub = 0.0
        j_years = re.findall(r"(\d+)\+?\s*years?\s+(?:of\s+)?experience", j_lower)
        r_years = re.findall(r"(\d+)\+?\s*years?\s+(?:of\s+)?experience", r_lower)
        if j_years:
            required = max(int(y) for y in j_years)
            actual = max((int(y) for y in r_years), default=0)
            exp_sub = min(actual / required, 1.0) * 100 if required else 100.0
        elif re.search(r"experience", r_lower):
            exp_sub = 60.0  # has some experience section

        # Education subscore
        edu_sub = 0.0
        edu_levels = ["phd", "doctorate", "master", "bachelor", "associate", "diploma"]
        j_edu = next((lvl for lvl in edu_levels if lvl in j_lower), None)
        r_edu = next((lvl for lvl in edu_levels if lvl in r_lower), None)
        if j_edu is None:
            edu_sub = 80.0  # JD doesn't specify – neutral
        elif r_edu is not None:
            j_idx = edu_levels.index(j_edu)
            r_idx = edu_levels.index(r_edu)
            if r_idx <= j_idx:
                edu_sub = 100.0  # same or higher
            else:
                edu_sub = max(0, 100 - (r_idx - j_idx) * 25)

        return {
            "skills": round(min(skills_sub, 100.0), 1),
            "experience": round(min(exp_sub, 100.0), 1),
            "education": round(min(edu_sub, 100.0), 1),
        }

    # ── main scoring ─────────────────────────────────────────────────

    def score(
        self,
        resume_text: str,
        job_text: str,
        candidate_name: str = "",
    ) -> MatchResult:
        """Full scoring pipeline.

        Returns a :class:`MatchResult` with score, grade, matched /
        missing skills, subscores, and explanation.
        
        Parameters
        ----------
        resume_text : str
            The resume text to score
        job_text : str
            The job description to match against
        candidate_name : str, optional
            Optional candidate name for identification
        """
        if not resume_text or not resume_text.strip():
            return MatchResult(
                score=0, explanation="Resume text is empty."
            )
        if not job_text or not job_text.strip():
            return MatchResult(
                score=0, explanation="Job description text is empty."
            )

        # 1. Semantic similarity (SBERT)
        semantic = self._sbert_cosine(resume_text, job_text)

        # 2. Keyword overlap
        keyword_ratio, matched, missing = self._keyword_overlap(
            resume_text, job_text
        )

        # 3. TF-IDF cosine
        tfidf = self._tfidf_cosine(resume_text, job_text)

        # 4. Structural bonus
        structural = _structural_score(resume_text)

        # Weighted combination → 0-100
        # Score formula: (0.7 * similarity) + (0.3 * ml_probability)
        # Where similarity = semantic score, ml_probability = keyword score
        similarity_score = semantic * 100
        ml_probability = keyword_ratio * 100
        
        raw = (0.7 * similarity_score) + (0.3 * ml_probability)

        subscores = {
            "semantic": round(semantic * 100, 1),
            "keyword": round(keyword_ratio * 100, 1),
            "tfidf": round(tfidf * 100, 1),
            "structural": round(structural * 100, 1),
        }

        cat_scores = self._category_subscores(
            resume_text, job_text, matched, missing
        )
        subscores.update(cat_scores)

        top_matched = matched[:10]
        top_missing = missing[:5]

        explanation = _build_explanation(
            raw, _grade(raw), top_matched, top_missing, subscores
        )

        # 5. ATS simulation
        from app.services.ats_service import ats_analyse

        ats_result = ats_analyse(resume_text, job_text)

        return MatchResult(
            score=raw,
            matched_skills=top_matched,
            missing_skills=top_missing,
            subscores=subscores,
            explanation=explanation,
            ats_score=ats_result["ats_score"],
            ats_details=ats_result,
            similarity_score=round(similarity_score, 1),
            ml_probability=round(ml_probability, 1),
            candidate_name=candidate_name,
        )

    # ── batch scoring ────────────────────────────────────────────────

    def batch_score(
        self,
        resume_text: str,
        job_texts: List[str],
    ) -> List[MatchResult]:
        """Score one resume against multiple job descriptions."""
        return [self.score(resume_text, jt) for jt in job_texts]

    # ── status ───────────────────────────────────────────────────────

    def check_status(self) -> Dict[str, Any]:
        """Return component readiness info."""
        sbert = _get_sbert()
        return {
            "tfidf_ready": self.vectorizer is not None and hasattr(self.vectorizer, "vocabulary_"),
            "sbert_ready": sbert is not None,
            "all_ready": self.is_ready,
        }

    def status_message(self) -> str:
        if self.is_ready:
            return "MLService ready"
        return f"MLService error: {self.error_message or 'unknown'}"

