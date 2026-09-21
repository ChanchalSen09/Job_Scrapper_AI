"""
Tests for the profile-driven job scorer.

Tests 23 scenarios from the requirements including:
- Primary AI roles → high score
- Secondary roles → moderate (require AI content)
- Generic roles → low score
- Hard rejections (senior, over-experience, unrelated stack)
- Experience parsing edge cases
- Location scoring
- Score capping (AI keyword spam doesn't break the cap)
- Missing preferred vs required skills
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.scorer import JobScorer, check_hard_rejections, _get_band
import config


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def scorer():
    return JobScorer()


def make_job(
    title: str,
    description: str = '',
    location: str = 'Remote, India',
    company: str = 'TechCo',
    source: str = 'linkedin',
) -> dict:
    return {
        'title': title,
        'company': company,
        'location': location,
        'description': description,
        'source': source,
        'url': 'https://example.com/job/1',
    }


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1: AI Engineer → high score
# ─────────────────────────────────────────────────────────────────────────────

def test_ai_engineer_high_score(scorer):
    job = make_job(
        title='AI Engineer',
        description=(
            'We are looking for an AI Engineer to build RAG pipelines, '
            'integrate LLM APIs, work with LangChain, LangGraph, FastAPI, '
            'Python, PostgreSQL, and Redis. Experience with AI agents and '
            'agentic workflows required.'
        ),
    )
    result = scorer.score_and_explain(job)
    assert result['final_score'] >= 80, f"AI Engineer should score ≥80, got {result['final_score']}"
    assert result['match_band'] in ('STRONG', 'EXCELLENT')
    assert result['role_category'] == 'AI_CORE'
    assert result['is_rejected'] is False


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2: Full Stack AI Engineer → high score
# ─────────────────────────────────────────────────────────────────────────────

def test_full_stack_ai_engineer_high_score(scorer):
    job = make_job(
        title='Full Stack AI Engineer',
        description=(
            'Build AI-powered products using Python, FastAPI, React, TypeScript, '
            'LangChain, OpenAI API, vector search, PostgreSQL. Experience with '
            'AI agents and generative AI required.'
        ),
    )
    result = scorer.score_and_explain(job)
    assert result['final_score'] >= 80
    assert result['match_band'] in ('STRONG', 'EXCELLENT')
    assert result['is_rejected'] is False


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3: GenAI Engineer → high score
# ─────────────────────────────────────────────────────────────────────────────

def test_genai_engineer_high_score(scorer):
    job = make_job(
        title='Generative AI Engineer',
        description=(
            'Work on GenAI applications using Gemini API, LangGraph, RAG pipelines, '
            'embeddings, vector databases (Qdrant), FastAPI, Python.'
        ),
    )
    result = scorer.score_and_explain(job)
    # GenAI roles without listed backend experience still score GOOD (70+) and are notify-worthy
    assert result['final_score'] >= 70, f"GenAI Engineer should score >=70, got {result['final_score']}"
    assert result['match_band'] in ('GOOD', 'STRONG', 'EXCELLENT')


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4: RAG Engineer → high score
# ─────────────────────────────────────────────────────────────────────────────

def test_rag_engineer_high_score(scorer):
    job = make_job(
        title='RAG Engineer',
        description=(
            'Build retrieval-augmented generation systems using LangChain, '
            'Qdrant, semantic search, embeddings, Python, FastAPI. '
            'Experience with LLM APIs essential.'
        ),
    )
    result = scorer.score_and_explain(job)
    # RAG Engineer is a strong AI match — should be GOOD or better (notify-worthy)
    assert result['final_score'] >= 70, f"RAG Engineer should score >=70, got {result['final_score']}"
    assert result['role_category'] == 'RAG'


# ─────────────────────────────────────────────────────────────────────────────
# TEST 5: Agentic AI Engineer → high score
# ─────────────────────────────────────────────────────────────────────────────

def test_agentic_ai_engineer_high_score(scorer):
    job = make_job(
        title='Agentic AI Engineer',
        description=(
            'Design and build multi-agent systems using LangGraph, AI agents, '
            'agentic workflows, tool calling, human-in-the-loop, guardrails, '
            'Python, FastAPI.'
        ),
    )
    result = scorer.score_and_explain(job)
    assert result['final_score'] >= 70, f"Agentic AI Engineer should score >=70, got {result['final_score']}"
    assert result['role_category'] == 'AGENTIC_AI'


# ─────────────────────────────────────────────────────────────────────────────
# TEST 6: Python Backend + AI context → strong
# ─────────────────────────────────────────────────────────────────────────────

def test_python_backend_with_ai_strong(scorer):
    job = make_job(
        title='Python Backend Engineer',
        description=(
            'Build AI backend services using FastAPI, Python, PostgreSQL, Redis. '
            'Integrate LLM APIs, implement RAG pipelines, work with LangChain. '
            'The product is an AI-powered knowledge management platform.'
        ),
    )
    result = scorer.score_and_explain(job)
    # Python Backend with heavy AI content should be notify-worthy (GOOD+)
    assert result['final_score'] >= 65, f"Python Backend with AI should score >=65, got {result['final_score']}"
    assert result['match_band'] in ('GOOD', 'STRONG', 'EXCELLENT')


# ─────────────────────────────────────────────────────────────────────────────
# TEST 7: Generic Python Developer → lower score
# ─────────────────────────────────────────────────────────────────────────────

def test_generic_python_developer_lower_score(scorer):
    job = make_job(
        title='Python Developer',
        description=(
            'Work on our e-commerce platform using Django, PostgreSQL, REST API. '
            'Build CRUD features and maintain existing backend systems.'
        ),
    )
    result = scorer.score_and_explain(job)
    assert result['final_score'] < 70, f"Generic Python Dev should score <70, got {result['final_score']}"
    assert result['match_band'] in ('BORDERLINE', 'SKIP')


# ─────────────────────────────────────────────────────────────────────────────
# TEST 8: Generic React Developer → low score
# ─────────────────────────────────────────────────────────────────────────────

def test_generic_react_developer_low_score(scorer):
    job = make_job(
        title='React Developer',
        description=(
            'Build UI components using React.js, TypeScript, Redux, CSS. '
            'Work with REST APIs. No backend work involved.'
        ),
    )
    result = scorer.score_and_explain(job)
    assert result['final_score'] < 60, f"Generic React Dev should score <60, got {result['final_score']}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 9: Senior AI Engineer 5+ years → rejected
# ─────────────────────────────────────────────────────────────────────────────

def test_senior_ai_engineer_5_years_rejected(scorer):
    job = make_job(
        title='Senior AI Engineer',
        description='Requires 5+ years of experience. Lead the AI team.',
    )
    result = scorer.score_and_explain(job)
    assert result['is_rejected'] is True, 'Senior AI Engineer should be hard-rejected'
    assert result['final_score'] == 0


# ─────────────────────────────────────────────────────────────────────────────
# TEST 10: ML Research role → rejected/low
# ─────────────────────────────────────────────────────────────────────────────

def test_ml_research_role_rejected(scorer):
    job = make_job(
        title='ML Research Engineer',
        description=(
            'PhD required. PyTorch research, TensorFlow research, model architecture, '
            'deep learning research, NLP research, computer vision research. '
            'Publish papers. Model training at scale.'
        ),
    )
    result = scorer.score_and_explain(job)
    # Should be rejected or very low score
    assert result['is_rejected'] is True or result['final_score'] < 60, (
        f"ML Research should be rejected or low, got score={result['final_score']}, rejected={result['is_rejected']}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TEST 11: Remote India AI role → positive location score
# ─────────────────────────────────────────────────────────────────────────────

def test_remote_india_positive_location(scorer):
    job = make_job(
        title='AI Engineer',
        description='Build AI applications with Python, FastAPI, RAG, LangChain.',
        location='Remote, India',
    )
    result = scorer.score_and_explain(job)
    assert result['location_score'] >= 25, f"Remote India should get high location score, got {result['location_score']}"
    assert result['work_type'] == 'remote'


# ─────────────────────────────────────────────────────────────────────────────
# TEST 12: Onsite Bangalore AI role → positive
# ─────────────────────────────────────────────────────────────────────────────

def test_onsite_bangalore_positive(scorer):
    job = make_job(
        title='AI Engineer',
        description='Build AI applications with Python, FastAPI, RAG.',
        location='Bangalore, Karnataka',
    )
    result = scorer.score_and_explain(job)
    assert result['location_score'] > 0, 'Bangalore should get positive location score'
    assert result['work_type'] == 'onsite'
    assert result['is_rejected'] is False


# ─────────────────────────────────────────────────────────────────────────────
# TEST 13: Unsupported location → no location score
# ─────────────────────────────────────────────────────────────────────────────

def test_unsupported_location_no_score(scorer):
    job = make_job(
        title='AI Engineer',
        description='Build AI applications with Python, FastAPI, RAG, LangChain.',
        location='London, UK',
    )
    result = scorer.score_and_explain(job)
    assert result['location_score'] == 0, f"UK location should get 0 score, got {result['location_score']}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 14: 1-3 years experience → strong experience score
# ─────────────────────────────────────────────────────────────────────────────

def test_experience_1_3_years_strong(scorer):
    job = make_job(
        title='AI Engineer',
        description='Requirements: 1-3 years of experience. Build LLM applications with Python, FastAPI.',
    )
    result = scorer.score_and_explain(job)
    assert result['experience_score'] >= 80, f"1-3 years should score ≥80, got {result['experience_score']}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 15: 2+ years experience → acceptable
# ─────────────────────────────────────────────────────────────────────────────

def test_experience_2_plus_acceptable(scorer):
    job = make_job(
        title='AI Engineer',
        description='2+ years of experience required. Work with LLMs, RAG, Python.',
    )
    result = scorer.score_and_explain(job)
    assert result['experience_score'] >= 50, f"2+ years should be acceptable, got {result['experience_score']}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 16: 4+ years required → hard rejected
# ─────────────────────────────────────────────────────────────────────────────

def test_experience_4_plus_rejected(scorer):
    job = make_job(
        title='AI Engineer',
        description='Minimum 4 years of experience required. Work with LLMs and Python.',
    )
    result = scorer.score_and_explain(job)
    assert result['is_rejected'] is True, f"4+ years required should be hard-rejected"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 17: Duplicate URLs → handled in deduplication
# ─────────────────────────────────────────────────────────────────────────────

def test_duplicate_url_deduplication():
    from utils.helpers import normalize_url
    from services.processor import _deduplicate_urls

    jobs = [
        {'url': 'https://linkedin.com/jobs/1234', 'title': 'AI Engineer', 'company': 'Co A'},
        {'url': 'https://linkedin.com/jobs/1234', 'title': 'AI Engineer', 'company': 'Co A'},  # duplicate
        {'url': 'https://linkedin.com/jobs/5678', 'title': 'ML Engineer', 'company': 'Co B'},
    ]
    unique = _deduplicate_urls(jobs)
    assert len(unique) == 2, f"Expected 2 unique jobs, got {len(unique)}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 18: Duplicate company+title → deduplicated
# ─────────────────────────────────────────────────────────────────────────────

def test_duplicate_company_title_deduplication():
    from services.processor import _deduplicate_urls

    jobs = [
        {'url': 'https://naukri.com/job/1', 'title': 'AI Engineer', 'company': 'TechCo'},
        {'url': 'https://linkedin.com/jobs/2', 'title': 'AI Engineer', 'company': 'TechCo'},  # same co+title
        {'url': 'https://naukri.com/job/3', 'title': 'ML Engineer', 'company': 'TechCo'},
    ]
    unique = _deduplicate_urls(jobs)
    assert len(unique) == 2, f"Expected 2 unique jobs after company+title dedup, got {len(unique)}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 19: Stale jobs → score/band adjusted
# ─────────────────────────────────────────────────────────────────────────────

def test_stale_job_freshness_penalty(scorer):
    from services.processor import _apply_freshness

    job = make_job(title='AI Engineer', description='LLM RAG Python FastAPI LangGraph')
    result = scorer.score_and_explain(job)
    job.update(result)
    original_score = job['final_score']

    # Simulate 20 days old
    job['posted_date'] = '20 days ago'
    _apply_freshness(job)

    assert job['final_score'] == 0, f"20-day old job should score 0, got {job['final_score']}"
    assert job['match_band'] == 'SKIP'


# ─────────────────────────────────────────────────────────────────────────────
# TEST 20: Missing description → handled safely
# ─────────────────────────────────────────────────────────────────────────────

def test_missing_description_safe(scorer):
    job = {
        'title': 'AI Engineer',
        'company': 'TechCo',
        'location': 'Remote, India',
        'description': '',
        'source': 'linkedin',
        'url': 'https://example.com/job/99',
    }
    result = scorer.score_and_explain(job)
    assert 'final_score' in result
    assert isinstance(result['final_score'], int)
    # Title alone should still give decent role match
    assert result['role_score'] >= 60


# ─────────────────────────────────────────────────────────────────────────────
# TEST 21: AI keyword repeated 20 times → score remains capped
# ─────────────────────────────────────────────────────────────────────────────

def test_ai_keyword_spam_capped(scorer):
    # Repeat "rag" and "llm" 20 times each
    spam = ' '.join(['rag llm langchain langgraph agentic ai'] * 20)
    job = make_job(
        title='AI Engineer',
        description=spam,
    )
    result = scorer.score_and_explain(job)
    assert result['ai_score'] <= 100, f"AI score should be ≤100 (normalized), got {result['ai_score']}"
    assert result['final_score'] <= 100, f"Final score should never exceed 100, got {result['final_score']}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 22: Preferred missing skill → does NOT strongly penalize
# ─────────────────────────────────────────────────────────────────────────────

def test_preferred_skill_missing_no_reject(scorer):
    # Job prefers Kubernetes but Chanchal doesn't have it — should still score decently
    job = make_job(
        title='AI Engineer',
        description=(
            'Build AI applications with Python, FastAPI, LangChain, RAG pipelines. '
            'Kubernetes is preferred but not required. PostgreSQL, Redis experience needed.'
        ),
    )
    result = scorer.score_and_explain(job)
    # AI Engineer + Python/FastAPI + RAG + LangChain should be notify-worthy
    # Missing preferred skill (Kubernetes) should not tank the score below BORDERLINE
    assert result['final_score'] >= 60, (
        f"Missing preferred skill should not strongly penalize, got {result['final_score']}"
    )
    assert result['is_rejected'] is False


# ─────────────────────────────────────────────────────────────────────────────
# TEST 23: Match reason generated for notifiable job
# ─────────────────────────────────────────────────────────────────────────────

def test_match_reason_generated(scorer):
    job = make_job(
        title='AI Backend Engineer',
        description=(
            'Build AI backend services. Python, FastAPI, RAG pipelines, LangGraph, '
            'PostgreSQL, Redis. AI agents and agentic workflows. 1-3 years experience.'
        ),
        location='Remote, India',
    )
    result = scorer.score_and_explain(job)
    assert result['match_reason'] != '', 'Match reason should be generated'
    assert result['rejection_reason'] is None or result['rejection_reason'] == ''
    assert result['is_rejected'] is False


# ─────────────────────────────────────────────────────────────────────────────
# BAND UTILITY TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_band_boundaries():
    assert _get_band(95) == 'EXCELLENT'
    assert _get_band(90) == 'EXCELLENT'
    assert _get_band(89) == 'STRONG'
    assert _get_band(80) == 'STRONG'
    assert _get_band(79) == 'GOOD'
    assert _get_band(55) == 'GOOD'
    assert _get_band(54) == 'BORDERLINE'
    assert _get_band(40) == 'BORDERLINE'
    assert _get_band(39) == 'SKIP'
    assert _get_band(0) == 'SKIP'
