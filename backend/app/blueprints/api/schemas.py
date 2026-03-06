"""
Marshmallow schemas for API v1 request / response validation.
"""

from __future__ import annotations

from marshmallow import Schema, fields, validate


# ── Request schemas ──────────────────────────────────────────────────

class MatchRequestSchema(Schema):
    resume_text = fields.String(
        required=True,
        validate=validate.Length(min=50, error="resume_text must be at least 50 characters"),
    )
    job_description = fields.String(
        required=True,
        validate=validate.Length(min=50, error="job_description must be at least 50 characters"),
    )


class BatchMatchRequestSchema(Schema):
    resume_texts = fields.List(
        fields.String(validate=validate.Length(min=50)),
        required=True,
        validate=validate.Length(min=1, max=100, error="Provide 1-100 resume texts"),
    )
    resume_filenames = fields.List(
        fields.String(),
        required=False,
        missing=None,
        allow_none=True,
    )
    job_description = fields.String(
        required=True,
        validate=validate.Length(min=50, error="job_description must be at least 50 characters"),
    )
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))


class ParseRequestSchema(Schema):
    resume_text = fields.String(
        required=True,
        validate=validate.Length(min=20, error="resume_text must be at least 20 characters"),
    )


class FeedbackRequestSchema(Schema):
    resume_text = fields.String(
        required=True,
        validate=validate.Length(min=50),
    )
    job_description = fields.String(
        required=True,
        validate=validate.Length(min=50),
    )
    corrected_score = fields.Float(
        required=True,
        validate=validate.Range(min=0, max=100, error="corrected_score must be 0-100"),
    )
    comment = fields.String(load_default="")


# ── Response schemas ─────────────────────────────────────────────────

class SubscoresSchema(Schema):
    semantic = fields.Float()
    keyword = fields.Float()
    tfidf = fields.Float()
    structural = fields.Float()
    skills = fields.Float()
    experience = fields.Float()
    education = fields.Float()


class MatchResultSchema(Schema):
    rank = fields.Integer()
    candidate_name = fields.String()
    score = fields.Float()
    similarity_score = fields.Float()
    ml_probability = fields.Float()
    grade = fields.String()
    matched_skills = fields.List(fields.String())
    missing_skills = fields.List(fields.String())
    subscores = fields.Nested(SubscoresSchema)
    explanation = fields.String()
    ats_score = fields.Float()
    ats_details = fields.Dict(keys=fields.String(), values=fields.Raw())


class ContactSchema(Schema):
    emails = fields.List(fields.String())
    phones = fields.List(fields.String())
    linkedin = fields.String()


class EducationSchema(Schema):
    degree = fields.String()
    institution = fields.String()
    year = fields.String()


class ExperienceSchema(Schema):
    title = fields.String()
    company = fields.String()
    duration = fields.String()
    years = fields.Float()
    responsibilities = fields.String()


class ResumeProfileSchema(Schema):
    name = fields.String()
    contact = fields.Nested(ContactSchema)
    skills = fields.List(fields.String())
    education = fields.List(fields.Nested(EducationSchema))
    experience = fields.List(fields.Nested(ExperienceSchema))
    certifications = fields.List(fields.String())
    organizations = fields.List(fields.String())
    completeness_score = fields.Integer()
    career_timeline = fields.Dict(keys=fields.String(), values=fields.Raw())


class MetaSchema(Schema):
    latency_ms = fields.Float()


class HealthComponentSchema(Schema):
    ok = fields.Boolean()


class HealthDataSchema(Schema):
    status = fields.String()
    nlp_model = fields.Nested(HealthComponentSchema)
    ml_service = fields.Nested(HealthComponentSchema)
    storage = fields.Nested(HealthComponentSchema)


# ── Job / async schemas ──────────────────────────────────────────────

class JobStatusSchema(Schema):
    job_id = fields.String()
    state = fields.String()
    progress = fields.Integer()
    current = fields.Integer()
    total = fields.Integer()


class MatchHistorySchema(Schema):
    id = fields.Integer()
    score = fields.Float()
    grade = fields.String()
    matched_skills = fields.String()
    missing_skills = fields.String()
    created_at = fields.DateTime()


class ScrapeRequestSchema(Schema):
    url = fields.Url(
        required=True,
        schemes={"http", "https"},
    )


class ScrapeResultSchema(Schema):
    url = fields.String()
    title = fields.String()
    company = fields.String()
    location = fields.String()
    requirements = fields.List(fields.String())
    salary_range = fields.String()
    raw_description = fields.String()
    scraped_at = fields.String()
