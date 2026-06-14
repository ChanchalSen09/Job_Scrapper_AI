import re
from html import unescape
from typing import Optional
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs

def normalize_url(url: str) -> str:
    if not url:
        return ''
    try:
        parsed = urlparse(url)
        scheme = 'https'
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip('/')
        if not path:
            path = ''
        tracking_prefixes = ('utm_', 'ref', 'source', 'fbclid', 'gclid', 'mc_')
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=True)
            clean_params = {k: v for (k, v) in params.items() if not any((k.lower().startswith(prefix) for prefix in tracking_prefixes))}
            query = urlencode(clean_params, doseq=True) if clean_params else ''
        else:
            query = ''
        return urlunparse((scheme, netloc, path, '', query, ''))
    except Exception:
        return url.strip()

def clean_html(text: str) -> str:
    if not text:
        return ''
    clean = re.sub('<[^>]+>', ' ', text)
    clean = unescape(clean)
    clean = re.sub('\\s+', ' ', clean).strip()
    return clean

def extract_experience(text: str) -> Optional[int]:
    if not text:
        return None
    text_lower = text.lower()
    range_patterns = ['(\\d+)\\s*[-–]\\s*(\\d+)\\s*(?:years?|yrs?)', '(\\d+)\\s*to\\s*(\\d+)\\s*(?:years?|yrs?)']
    max_exp = None
    for pattern in range_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            try:
                high = int(match[1])
                if max_exp is None or high < max_exp:
                    max_exp = high
                elif max_exp is not None and high > max_exp:
                    pass
            except (ValueError, IndexError):
                continue
    if max_exp is not None:
        return max_exp
    plus_patterns = ['(\\d+)\\+\\s*(?:years?|yrs?)', '(?:minimum|min|at least)\\s*(\\d+)\\s*(?:years?|yrs?)']
    for pattern in plus_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            try:
                val = int(match) if isinstance(match, str) else int(match[0])
                if max_exp is None or val < max_exp:
                    max_exp = val
            except (ValueError, IndexError):
                continue
    return max_exp

def truncate_text(text: str, max_len: int=200) -> str:
    if not text or len(text) <= max_len:
        return text or ''
    return text[:max_len - 3] + '...'

def format_search_term_for_url(term: str) -> str:
    return term.lower().replace(' ', '+')

def format_search_term_for_slug(term: str) -> str:
    return term.lower().replace(' ', '-')