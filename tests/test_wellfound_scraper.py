"""Tests for WellfoundScraper JSON parsing (unit tests, no browser needed)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from scrapers.wellfound import WellfoundScraper, _dedup, _extract_work_type_from_json, _normalize_posted_date


@pytest.fixture
def scraper():
    return WellfoundScraper()


# ── _is_job_object

def test_is_job_object_with_title_and_company(scraper):
    # Now requires id/url/slug as well
    obj = {'title': 'AI Engineer', 'company': {'name': 'StartupCo'}, 'id': '123'}
    assert scraper._is_job_object(obj) is True

def test_is_job_object_with_title_and_slug_fails_without_company(scraper):
    # Without company, it should fail
    obj = {'title': 'Backend Engineer', 'slug': 'backend-engineer-123'}
    assert scraper._is_job_object(obj) is False

def test_is_job_object_missing_title(scraper):
    obj = {'company': {'name': 'Co'}, 'url': 'https://wellfound.com/jobs/1'}
    assert scraper._is_job_object(obj) is False

def test_is_job_object_minimal_keys(scraper):
    obj = {'description': 'We are hiring'}
    assert scraper._is_job_object(obj) is False


# ── _extract_job_from_json

def test_extract_job_basic(scraper):
    obj = {
        'title': 'AI Engineer',
        'company': {'name': 'NexusAI', 'slug': 'nexus-ai'},
        'location': 'Remote, India',
        'slug': 'ai-engineer-123',
        'description': 'Build LLM applications with Python and FastAPI.',
    }
    job = scraper._extract_job_from_json(obj)
    assert job is not None
    assert job['title'] == 'AI Engineer'
    assert job['company'] == 'NexusAI'
    assert 'wellfound.com' in job['url']
    assert job['source'] == 'wellfound'

def test_extract_job_missing_title_returns_none(scraper):
    obj = {'company': {'name': 'Co'}, 'slug': 'job-123'}
    assert scraper._extract_job_from_json(obj) is None

def test_extract_job_remote_flag(scraper):
    obj = {
        'title': 'Python Engineer',
        'company': {'name': 'StartupCo', 'slug': 'startup-co'},
        'remote': True,
        'slug': 'python-eng-456',
    }
    job = scraper._extract_job_from_json(obj)
    assert job is not None
    assert job['work_type'] == 'remote'
    assert 'Remote' in job['location']

def test_extract_job_list_location(scraper):
    obj = {
        'title': 'Full Stack AI Engineer',
        'company': {'name': 'AICo', 'slug': 'ai-co'},
        'locationNames': ['Bangalore', 'Remote'],
        'slug': 'fs-ai-789',
    }
    job = scraper._extract_job_from_json(obj)
    assert job is not None
    assert 'Bangalore' in job['location'] or 'Remote' in job['location']

def test_extract_job_explicit_url(scraper):
    obj = {
        'title': 'GenAI Engineer',
        'company': {'name': 'AIStartup', 'slug': 'ai-startup'},
        'url': 'https://wellfound.com/company/ai-startup/jobs/genai-engineer-1',
    }
    job = scraper._extract_job_from_json(obj)
    assert job is not None
    assert job['url'] == 'https://wellfound.com/company/ai-startup/jobs/genai-engineer-1'

def test_extract_job_no_url_no_slug_returns_none(scraper):
    obj = {
        'title': 'AI Engineer',
        'company': {'name': 'Co'},
        # No url, no slug — can't construct valid URL
    }
    job = scraper._extract_job_from_json(obj)
    assert job is None


# ── _parse_json_data (recursive)

def test_parse_json_nested(scraper):
    data = {
        'props': {
            'jobs': [
                {
                    'title': 'AI Engineer',
                    'company': {'name': 'Co A', 'slug': 'co-a'},
                    'slug': 'ai-eng-1',
                    'remote': True,
                },
                {
                    'title': 'ML Engineer',
                    'company': {'name': 'Co B', 'slug': 'co-b'},
                    'slug': 'ml-eng-2',
                },
            ]
        }
    }
    jobs = scraper._parse_json_data(data)
    assert len(jobs) == 2
    titles = [j['title'] for j in jobs]
    assert 'AI Engineer' in titles
    assert 'ML Engineer' in titles


# ── Deduplication

def test_dedup_removes_duplicate_urls():
    jobs = [
        {'url': 'https://wellfound.com/jobs/1', 'title': 'A'},
        {'url': 'https://wellfound.com/jobs/1', 'title': 'A'},  # dup
        {'url': 'https://wellfound.com/jobs/2', 'title': 'B'},
    ]
    unique = _dedup(jobs)
    assert len(unique) == 2

def test_dedup_skips_empty_url():
    jobs = [
        {'url': '', 'title': 'A'},
        {'url': 'https://wellfound.com/jobs/1', 'title': 'B'},
    ]
    unique = _dedup(jobs)
    assert len(unique) == 1


# ── Work type inference

def test_work_type_remote_flag():
    obj = {'remote': True}
    assert _extract_work_type_from_json(obj, '') == 'remote'

def test_work_type_location_hybrid():
    assert _extract_work_type_from_json({}, 'Hybrid, Bangalore') == 'hybrid'

def test_work_type_location_onsite():
    assert _extract_work_type_from_json({}, 'Bangalore') == 'onsite'

def test_work_type_unknown():
    assert _extract_work_type_from_json({}, 'London') == 'unknown'


# ── Posted date normalization

def test_normalize_posted_date_iso():
    assert _normalize_posted_date('2026-09-15T10:30:00Z') == '2026-09-15'

def test_normalize_posted_date_relative():
    assert _normalize_posted_date('3 days ago') == '3 days ago'

def test_normalize_posted_date_empty():
    assert _normalize_posted_date('') == ''
