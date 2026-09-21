import re
from html import unescape
from typing import Optional
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs

# ─────────────────────────────────────────────────────────────────────────────
# URL UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

# Tracking parameters to strip from URLs
_TRACKING_PREFIXES = (
    'utm_', 'ref', 'source', 'fbclid', 'gclid', 'mc_',
    'trk', 'trkInfo', 'refId', 'trackingId', 'campaign',
)


def normalize_url(url: str) -> str:
    """Normalize a URL: lowercase netloc, strip tracking params, ensure https."""
    if not url:
        return ''
    # Ensure scheme exists before parsing so netloc is correctly identified
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url
        
    try:
        parsed = urlparse(url)
        scheme = 'https'
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip('/')
        if not path:
            path = ''
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=True)
            clean_params = {
                k: v for k, v in params.items()
                if not any(k.lower().startswith(prefix) for prefix in _TRACKING_PREFIXES)
            }
            query = urlencode(clean_params, doseq=True) if clean_params else ''
        else:
            query = ''
        return urlunparse((scheme, netloc, path, '', query, ''))
    except Exception:
        return url.strip()


# ─────────────────────────────────────────────────────────────────────────────
# TEXT UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def clean_html(text: str) -> str:
    """Strip HTML tags, unescape entities, collapse whitespace."""
    if not text:
        return ''
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = unescape(clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def truncate_text(text: str, max_len: int = 200) -> str:
    if not text or len(text) <= max_len:
        return text or ''
    return text[:max_len - 3] + '...'


def normalize_title(title: str) -> str:
    """Normalize a job title for deduplication (lowercase, collapse spaces, strip punctuation)."""
    if not title:
        return ''
    t = title.lower()
    t = re.sub(r'[^a-z0-9 ]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


# ─────────────────────────────────────────────────────────────────────────────
# EXPERIENCE PARSING
# ─────────────────────────────────────────────────────────────────────────────

def parse_experience_requirement(text: str) -> dict:
    """
    Parse experience requirement from job description text.

    Returns a structured dict:
    {
        "min": int | None,
        "max": int | None,
        "is_range": bool,       # "1-3 years"
        "is_plus": bool,        # "2+ years"
        "is_preferred": bool,   # "3 years preferred"
        "is_required": bool,    # "3 years required" / "minimum 3 years"
        "freshers_welcome": bool,
        "raw_text": str,
    }
    """
    if not text:
        return _empty_exp()

    text_lower = text.lower()

    # ── Freshers welcome
    fresher_patterns = [
        r'\bfreshers?\s+(?:are\s+)?welcome\b',
        r'\b0\s*[-–]\s*[12]\s*(?:years?|yrs?)\b',
        r'\bentry[-\s]level\b',
        r'\bno\s+experience\s+required\b',
    ]
    for p in fresher_patterns:
        if re.search(p, text_lower):
            return {
                'min': 0, 'max': 2, 'is_range': True,
                'is_plus': False, 'is_preferred': False, 'is_required': False,
                'freshers_welcome': True, 'raw_text': _extract_exp_snippet(text_lower),
            }

    # ── Range patterns: "1-3 years", "1 to 3 years", "1 – 3 years"
    range_patterns = [
        r'(\d+)\s*[-–to]+\s*(\d+)\s*(?:years?|yrs?)\s*(of\s+experience)?',
        r'(\d+)\s+to\s+(\d+)\s*(?:years?|yrs?)',
    ]
    for pattern in range_patterns:
        m = re.search(pattern, text_lower)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            # Determine preferred vs required
            snippet = text_lower[max(0, m.start() - 30): m.end() + 30]
            is_preferred = bool(re.search(r'\bpreferred\b|\bnice\s+to\s+have\b|\bbonus\b', snippet))
            is_required = not is_preferred
            return {
                'min': lo, 'max': hi, 'is_range': True,
                'is_plus': False, 'is_preferred': is_preferred, 'is_required': is_required,
                'freshers_welcome': lo == 0, 'raw_text': m.group(0),
            }

    # ── Plus patterns: "2+ years", "minimum 3 years", "at least 2 years"
    plus_patterns = [
        r'(\d+)\s*\+\s*(?:years?|yrs?)',
        r'(?:minimum|min|at\s+least)\s+(\d+)\s*(?:years?|yrs?)',
        r'(\d+)\s*(?:years?|yrs?)\s*(?:minimum|min)',
    ]
    for pattern in plus_patterns:
        m = re.search(pattern, text_lower)
        if m:
            # The capturing group for the number may be group 1 in all cases
            val = int(m.group(1))
            snippet = text_lower[max(0, m.start() - 30): m.end() + 30]
            is_preferred = bool(re.search(r'\bpreferred\b|\bnice\s+to\s+have\b|\bbonus\b', snippet))
            is_required = not is_preferred
            return {
                'min': val, 'max': None, 'is_range': False,
                'is_plus': True, 'is_preferred': is_preferred, 'is_required': is_required,
                'freshers_welcome': False, 'raw_text': m.group(0),
            }

    # ── Exact: "3 years of experience" / "3 years experience" / "3 years preferred"
    exact_patterns = [
        r'(\d+)\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)',
        r'(\d+)\s*(?:years?|yrs?)\s+(?:preferred|required|minimum)',
        r'experience\s+(?:of\s+)?(\d+)\s*(?:years?|yrs?)',
        r'(\d+)\s*(?:years?|yrs?)',   # broad fallback
    ]
    for pattern in exact_patterns:
        m = re.search(pattern, text_lower)
        if m:
            val = int(m.group(1))
            snippet = text_lower[max(0, m.start() - 30): m.end() + 50]
            is_preferred = bool(re.search(r'\bpreferred\b|\bnice\s+to\s+have\b|\bbonus\b|\bideally\b|\bdesirable\b', snippet))
            is_required = not is_preferred
            return {
                'min': val, 'max': val, 'is_range': False,
                'is_plus': False, 'is_preferred': is_preferred, 'is_required': is_required,
                'freshers_welcome': False, 'raw_text': m.group(0),
            }

    return _empty_exp()


def _empty_exp() -> dict:
    return {
        'min': None, 'max': None, 'is_range': False,
        'is_plus': False, 'is_preferred': False, 'is_required': False,
        'freshers_welcome': False, 'raw_text': '',
    }


def _extract_exp_snippet(text: str) -> str:
    """Extract a short snippet around experience mentions."""
    m = re.search(r'.{0,20}\d.{0,20}(?:years?|yrs?).{0,20}', text)
    return m.group(0) if m else ''


def extract_experience(text: str) -> Optional[int]:
    """
    Legacy function — returns a single int for backward compatibility.
    Returns the minimum required years, or None if not found.
    """
    req = parse_experience_requirement(text)
    return req.get('min')


# ─────────────────────────────────────────────────────────────────────────────
# WORK TYPE EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def extract_work_type(text: str) -> str:
    """
    Extract work type from job text.
    Returns one of: 'remote', 'hybrid', 'onsite', 'unknown'
    """
    if not text:
        return 'unknown'
    t = text.lower()

    remote_signals = ['remote', 'work from home', 'wfh', 'fully remote', 'anywhere in india', 'pan india']
    hybrid_signals = ['hybrid', 'partial remote', 'flexible work']

    for sig in remote_signals:
        if sig in t:
            return 'remote'
    for sig in hybrid_signals:
        if sig in t:
            return 'hybrid'
    # Check for on-site city mentions
    city_signals = ['bangalore', 'bengaluru', 'mumbai', 'delhi', 'hyderabad', 'pune',
                    'chennai', 'gurgaon', 'gurugram', 'noida', 'ahmedabad', 'jaipur', 'indore']
    for city in city_signals:
        if city in t:
            return 'onsite'
    return 'unknown'


# ─────────────────────────────────────────────────────────────────────────────
# FORMATTING UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def format_search_term_for_url(term: str) -> str:
    return term.lower().replace(' ', '+')


def format_search_term_for_slug(term: str) -> str:
    return term.lower().replace(' ', '-')