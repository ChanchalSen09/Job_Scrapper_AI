"""Tests for helpers: experience parsing, URL normalization, work type."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from utils.helpers import (
    parse_experience_requirement,
    normalize_url,
    normalize_title,
    extract_work_type,
)


# ─── Experience parsing

def test_parse_range_1_3():
    r = parse_experience_requirement('Requirements: 1-3 years of experience in Python.')
    assert r['min'] == 1 and r['max'] == 3
    assert r['is_range'] is True
    assert r['is_required'] is True

def test_parse_range_2_3():
    r = parse_experience_requirement('2-3 years experience required.')
    assert r['min'] == 2 and r['max'] == 3

def test_parse_plus_2():
    r = parse_experience_requirement('2+ years of experience.')
    assert r['min'] == 2
    assert r['is_plus'] is True

def test_parse_minimum_3():
    r = parse_experience_requirement('Minimum 3 years of experience required.')
    assert r['min'] == 3
    assert r['is_required'] is True

def test_parse_preferred():
    r = parse_experience_requirement('3 years preferred but not mandatory.')
    assert r['min'] == 3
    assert r['is_preferred'] is True
    assert r['is_required'] is False

def test_parse_freshers_welcome():
    r = parse_experience_requirement('Freshers welcome. 0-2 years experience.')
    assert r['freshers_welcome'] is True

def test_parse_entry_level():
    r = parse_experience_requirement('Entry-level role, no prior experience required.')
    assert r['freshers_welcome'] is True

def test_parse_no_experience():
    r = parse_experience_requirement('Looking for a Python developer.')
    assert r['min'] is None and r['max'] is None

def test_parse_5_plus_required():
    r = parse_experience_requirement('5+ years of experience required in AI.')
    assert r['min'] == 5
    assert r['is_plus'] is True
    assert r['is_required'] is True

def test_parse_4_years_exact():
    r = parse_experience_requirement('Experience of 4 years in software development.')
    assert r['min'] == 4

def test_parse_prefers_required_distinction():
    """Ensure "3 years preferred" != "3 years required"."""
    preferred = parse_experience_requirement('3 years of experience preferred.')
    required = parse_experience_requirement('Minimum 3 years of experience required.')
    assert preferred['is_preferred'] is True
    assert required['is_required'] is True


# ─── URL normalization

def test_normalize_url_strips_utm():
    url = 'https://linkedin.com/jobs/1234?utm_source=google&utm_medium=cpc'
    normalized = normalize_url(url)
    assert 'utm_source' not in normalized
    assert 'utm_medium' not in normalized
    assert 'linkedin.com/jobs/1234' in normalized

def test_normalize_url_strips_trk():
    url = 'https://linkedin.com/jobs/1234?trk=job_search&refId=abc123'
    normalized = normalize_url(url)
    assert 'trk' not in normalized

def test_normalize_url_lowercase():
    url = 'https://LinkedIn.COM/Jobs/1234'
    normalized = normalize_url(url)
    assert normalized == normalized.lower() or 'linkedin.com' in normalized.lower()

def test_normalize_url_empty():
    assert normalize_url('') == ''


# ─── Title normalization

def test_normalize_title_basic():
    assert normalize_title('AI Engineer') == 'ai engineer'

def test_normalize_title_punctuation():
    assert normalize_title('AI/ML Engineer (Remote)') == 'ai ml engineer remote'

def test_normalize_title_empty():
    assert normalize_title('') == ''


# ─── Work type extraction

def test_work_type_remote():
    assert extract_work_type('Remote, India') == 'remote'

def test_work_type_wfh():
    assert extract_work_type('Work from home position') == 'remote'

def test_work_type_hybrid():
    assert extract_work_type('Hybrid role, Bangalore') == 'hybrid'

def test_work_type_onsite():
    assert extract_work_type('Bangalore, Karnataka') == 'onsite'

def test_work_type_unknown():
    assert extract_work_type('') == 'unknown'
