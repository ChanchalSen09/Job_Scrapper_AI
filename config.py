import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# CREDENTIALS
# ─────────────────────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
CHAT_ID: str = os.getenv('CHAT_ID', '')
DATABASE_URL: str = os.getenv('DATABASE_URL', '')

# ─────────────────────────────────────────────────────────────────────────────
# SEARCH TERMS — AI-focused only. Secondary terms filtered heavily by scorer.
# ─────────────────────────────────────────────────────────────────────────────
SEARCH_TERMS: list[str] = [
    # Primary AI roles
    'AI Engineer',
    'AI Software Engineer',
    'AI Application Engineer',
    'AI Backend Engineer',
    'AI Full Stack Engineer',
    'Full Stack AI Engineer',
    'Generative AI Engineer',
    'GenAI Engineer',
    'Applied AI Engineer',
    'LLM Engineer',
    'LLM Application Engineer',
    'RAG Engineer',
    'Agentic AI Engineer',
    'AI Platform Engineer',
    'AI Solutions Engineer',
    # Python + AI combos
    'Python AI Engineer',
    'Python GenAI Engineer',
    'Python LLM Engineer',
    'Python RAG Engineer',
    'AI Backend Python',
    'GenAI FastAPI',
    'LLM FastAPI',
    # Secondary (filtered heavily by AI relevance scorer)
    'Python Backend Engineer',
    'Backend Engineer Python',
    'SDE 1 Python',
    'Full Stack Engineer Python',
]

# ─────────────────────────────────────────────────────────────────────────────
# WELLFOUND-SPECIFIC SEARCH TERMS
# Wellfound hosts early-stage AI startups. They often use simpler, less formal
# job titles. These terms are used only by the WellfoundScraper.
# ─────────────────────────────────────────────────────────────────────────────
WELLFOUND_SEARCH_TERMS: list[str] = [
    # Core AI roles
    'ai-engineer',
    'generative-ai-engineer',
    'llm-engineer',
    'rag-engineer',
    'machine-learning-engineer',
    'ai-backend-engineer',
    'full-stack-ai-engineer',
    # Startup-flavored titles
    'founding-ai-engineer',
    'founding-engineer',
    'python-engineer',
    'backend-engineer',
    'software-engineer',
]

# ─────────────────────────────────────────────────────────────────────────────
# TARGET ROLES — Primary (scored as AI roles)
# Values: raw title score points
# ─────────────────────────────────────────────────────────────────────────────
PRIMARY_AI_ROLES: dict[str, int] = {
    'ai engineer': 120,
    'full stack ai engineer': 120,
    'ai full stack engineer': 120,
    'generative ai engineer': 120,
    'genai engineer': 120,
    'applied ai engineer': 115,
    'ai software engineer': 110,
    'ai application engineer': 110,
    'ai backend engineer': 110,
    'llm engineer': 110,
    'llm application engineer': 110,
    'agentic ai engineer': 110,
    'rag engineer': 105,
    'ai platform engineer': 105,
    'ai solutions engineer': 100,
    'machine learning engineer': 80,  # Only high if strongly LLM/GenAI focused
}

# Secondary roles — require AI relevance to score well
SECONDARY_ROLES: dict[str, int] = {
    'python backend engineer': 75,
    'backend engineer': 70,
    'backend developer': 70,
    'software engineer': 60,
    'software developer': 55,
    'sde 1': 60,
    'sde1': 60,
    'sde-1': 60,
    'sde': 55,
    'full stack engineer': 55,
    'full stack developer': 50,
}

# Generic roles — low base score, need strong AI content to be relevant
GENERIC_ROLES: dict[str, int] = {
    'react developer': 45,
    'django developer': 45,
    'python developer': 45,
    'frontend developer': 45,
    'frontend engineer': 45,
}

# Backward-compat alias used in older code paths
TARGET_ROLES: dict[str, list[str]] = {
    'highest': list(PRIMARY_AI_ROLES.keys()),
    'secondary': list(SECONDARY_ROLES.keys()),
    'additional': list(GENERIC_ROLES.keys()),
}

# ─────────────────────────────────────────────────────────────────────────────
# HARD REJECTION — Roles and patterns that must be rejected
# ─────────────────────────────────────────────────────────────────────────────
EXCLUDED_TITLE_KEYWORDS: list[str] = [
    'senior', 'staff engineer', 'principal', 'lead engineer', 'tech lead',
    'engineering manager', 'architect', 'director', 'head of engineering',
    'vp of engineering', 'chief technology',
]

EXCLUDED_ROLE_TYPES: list[str] = [
    'data entry', 'business analyst', 'manual tester', 'qa engineer',
    'quality assurance', 'devops engineer', 'network engineer',
    'cybersecurity', 'embedded systems', 'hardware engineer',
    'salesforce', 'sap consultant', 'java developer', 'java engineer',
    '.net developer', 'php developer', 'ruby developer',
    'ios developer', 'android developer', 'mobile developer',
]

EXCLUDED_STACKS: list[str] = [
    'java spring', 'spring boot', 'hibernate', '.net core', 'asp.net',
    'ruby on rails', 'laravel', 'symfony', 'salesforce', 'sap',
    'matlab', 'r programming',
]

BANNED_COMPANIES: list[str] = [
    'turing', 'crossing hurdles',
]

# ─────────────────────────────────────────────────────────────────────────────
# AI RELEVANCE KEYWORDS — Points per keyword (capped at AI_SCORE_CAP)
# ─────────────────────────────────────────────────────────────────────────────
AI_KEYWORDS: dict[str, int] = {
    # Agent / Agentic
    'langgraph': 30,
    'agentic ai': 30,
    'agentic workflow': 30,
    'ai agent': 25,
    'ai agents': 25,
    'multi-agent': 25,
    'multi agent': 25,
    # RAG & Retrieval
    'rag': 30,
    'retrieval augmented': 25,
    'retrieval-augmented': 25,
    'vector search': 20,
    'vector database': 20,
    'vector store': 20,
    'semantic search': 20,
    # LLM
    'llm': 25,
    'large language model': 25,
    'langchain': 25,
    'generative ai': 25,
    'genai': 25,
    # Embeddings
    'embeddings': 20,
    'embedding pipeline': 20,
    # Vector DBs
    'qdrant': 20,
    'pinecone': 15,
    'weaviate': 15,
    'chroma': 15,
    # APIs & Engineering
    'tool calling': 20,
    'function calling': 20,
    'llm api': 20,
    'openai api': 15,
    'gemini api': 15,
    'anthropic': 15,
    'hugging face': 15,
    # Prompt / Context
    'prompt engineering': 15,
    'context engineering': 15,
    'system prompt': 10,
    # Safety & Evaluation
    'guardrails': 20,
    'ai guardrails': 20,
    'ai evaluation': 15,
    'ai safety': 10,
    # Human-in-loop
    'human-in-the-loop': 15,
    'human in the loop': 15,
    # General AI application
    'ai application': 20,
    'ai product': 15,
    'ai backend': 20,
    'ai orchestration': 15,
    'ollama': 15,
}

AI_SCORE_CAP: int = 180  # Max raw AI relevance points

# ─────────────────────────────────────────────────────────────────────────────
# BACKEND SKILLS — Points per skill (capped at BACKEND_SCORE_CAP)
# ─────────────────────────────────────────────────────────────────────────────
BACKEND_SKILLS: dict[str, int] = {
    'python': 20,
    'fastapi': 25,
    'django': 15,
    'django rest': 15,
    'rest api': 10,
    'restful': 10,
    'postgresql': 10,
    'redis': 10,
    'sqlalchemy': 10,
    'async python': 15,
    'asyncio': 15,
    'pydantic': 10,
    'microservices': 10,
    'websocket': 10,
    'mongodb': 8,
    'mysql': 8,
    'celery': 8,
}

BACKEND_SCORE_CAP: int = 100

# ─────────────────────────────────────────────────────────────────────────────
# FRONTEND SKILLS — Only weighted for AI Full Stack roles
# ─────────────────────────────────────────────────────────────────────────────
FRONTEND_SKILLS: dict[str, int] = {
    'react': 10,
    'react.js': 10,
    'react native': 5,
    'typescript': 10,
    'javascript': 5,
    'next.js': 8,
    'tailwind': 5,
    'redux': 5,
}

FRONTEND_SCORE_CAP: int = 35

# Full-stack AI role titles that get frontend bonus
FULLSTACK_AI_TITLES: list[str] = [
    'full stack ai engineer',
    'ai full stack engineer',
    'ai application engineer',
    'full stack engineer',
    'full stack developer',
]

# ─────────────────────────────────────────────────────────────────────────────
# CLOUD / DEVOPS — Supporting evidence only
# ─────────────────────────────────────────────────────────────────────────────
CLOUD_SKILLS: dict[str, int] = {
    'aws': 10,
    'amazon web services': 10,
    'ec2': 10,
    's3': 5,
    'docker': 10,
    'ci/cd': 5,
    'github actions': 5,
    'linux': 5,
    'kubernetes': 5,
    'gcp': 5,
    'azure': 5,
}

CLOUD_SCORE_CAP: int = 40

# ─────────────────────────────────────────────────────────────────────────────
# RESPONSIBILITY MATCH — Keywords in JD responsibilities section
# ─────────────────────────────────────────────────────────────────────────────
RESPONSIBILITY_KEYWORDS: dict[str, int] = {
    'build llm': 25,
    'build ai': 20,
    'integrate llm': 20,
    'rag pipeline': 25,
    'vector search': 20,
    'ai agent': 20,
    'agentic workflow': 25,
    'tool calling': 20,
    'ai backend': 20,
    'fastapi': 15,
    'python service': 15,
    'production ai': 20,
    'ai api': 20,
    'prompt engineering': 15,
    'guardrail': 20,
    'ai evaluation': 15,
    'ai orchestration': 15,
    'async backend': 15,
    'ai product': 15,
    'production debugging': 10,
    'document retrieval': 15,
    'embedding': 15,
}

RESPONSIBILITY_SCORE_CAP: int = 100

# ─────────────────────────────────────────────────────────────────────────────
# LOCATION — Target locations and tiers
# ─────────────────────────────────────────────────────────────────────────────
TARGET_LOCATIONS: list[str] = [
    'remote', 'india', 'bangalore', 'bengaluru', 'mumbai', 'delhi', 'ncr',
    'hyderabad', 'pune', 'chennai', 'gurgaon', 'gurugram', 'noida',
    'kolkata', 'ahmedabad', 'jaipur', 'indore', 'work from home', 'wfh',
]

REMOTE_KEYWORDS: list[str] = [
    'remote', 'work from home', 'wfh', 'anywhere in india', 'pan india',
    'fully remote', 'remote india',
]

HYBRID_KEYWORDS: list[str] = ['hybrid', 'partial remote', 'flexible']

TIER_1_CITIES: list[str] = [
    'bangalore', 'bengaluru', 'pune', 'hyderabad', 'mumbai',
    'delhi', 'ncr', 'gurgaon', 'gurugram', 'noida', 'chennai',
]

TIER_2_CITIES: list[str] = [
    'ahmedabad', 'jaipur', 'indore', 'kolkata', 'kochi',
]

# ─────────────────────────────────────────────────────────────────────────────
# EXPERIENCE LIMITS
# ─────────────────────────────────────────────────────────────────────────────
EXPERIENCE_HARD_REJECT_MIN: int = 4   # Reject if minimum required > this
EXPERIENCE_SOFT_REJECT_MIN: int = 3   # Penalize if minimum required > this
EXPERIENCE_MAX: int = 3               # Backward compat alias

# ─────────────────────────────────────────────────────────────────────────────
# SCORING WEIGHTS — Must sum to 1.0
# ─────────────────────────────────────────────────────────────────────────────
SCORING_WEIGHTS: dict[str, float] = {
    'role': 0.25,
    'ai': 0.25,
    'skill': 0.20,
    'responsibility': 0.15,
    'experience': 0.10,
    'location': 0.05,
}

# ─────────────────────────────────────────────────────────────────────────────
# MATCH BANDS
# ─────────────────────────────────────────────────────────────────────────────
MATCH_BANDS: dict[str, int] = {
    'EXCELLENT': 90,
    'STRONG': 80,
    'GOOD': 55,
    'BORDERLINE': 40,
    # Below 40 = SKIP
}

# Only notify these bands via Telegram
NOTIFY_BANDS: list[str] = ['EXCELLENT', 'STRONG', 'GOOD', 'BORDERLINE']

# Minimum final score (0-100) to save and notify
MIN_SCORE_THRESHOLD: int = 40

# ─────────────────────────────────────────────────────────────────────────────
# ROLE CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────
ROLE_CATEGORIES: dict[str, list[str]] = {
    # Specific roles FIRST — order matters for classification
    'AGENTIC_AI': ['agentic ai engineer', 'agentic ai', 'agentic engineer'],
    'RAG': ['rag engineer'],
    'LLM': ['llm engineer', 'llm application engineer'],
    'GENAI': ['generative ai engineer', 'genai engineer', 'applied ai engineer'],
    'AI_FULL_STACK': ['full stack ai engineer', 'ai full stack engineer', 'ai application engineer'],
    'AI_BACKEND': ['ai backend engineer', 'ai platform engineer', 'ai solutions engineer'],
    'AI_CORE': ['ai engineer', 'ai software engineer'],
    'ML_APPLIED': ['machine learning engineer'],
    'PYTHON_BACKEND': ['python backend engineer', 'backend engineer', 'backend developer'],
    'FULL_STACK': ['full stack engineer', 'full stack developer'],
    'GENERIC_BACKEND': ['software engineer', 'software developer', 'sde', 'sde 1', 'sde1'],
    'GENERIC': ['react developer', 'django developer', 'python developer'],
}

# ─────────────────────────────────────────────────────────────────────────────
# FRESHNESS WEIGHTS
# ─────────────────────────────────────────────────────────────────────────────
FRESHNESS_WEIGHTS: dict[str, float] = {
    '0-1': 1.0,    # today or yesterday
    '2-3': 0.9,    # 2-3 days old
    '4-7': 0.75,   # 4-7 days old
    '8-15': 0.5,   # 8-15 days old
    '15+': 0.0,    # older than 15 days — skip
}

# ─────────────────────────────────────────────────────────────────────────────
# SCRAPER SETTINGS
# ─────────────────────────────────────────────────────────────────────────────
MAX_PAGES_PER_SEARCH: int = 3
REQUEST_DELAY: tuple[float, float] = (2.0, 5.0)
PAGE_TIMEOUT: int = 30000
NAVIGATION_TIMEOUT: int = 30000

USER_AGENTS: list[str] = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
]

# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULER
# ─────────────────────────────────────────────────────────────────────────────
SCHEDULE_INTERVAL_HOURS: int = 2
NOTIFICATION_BATCH_SIZE: int = 5  # Jobs per Telegram message

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────
DATABASE_PATH: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jobs.db')
JOB_RETENTION_DAYS: int = 15

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────
LOG_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
LOG_FILE: str = os.path.join(LOG_DIR, 'app.log')
LOG_MAX_BYTES: int = 5 * 1024 * 1024
LOG_BACKUP_COUNT: int = 3

# Legacy — kept for backward compatibility with old code
SKILLS: list[str] = [
    'python', 'django', 'react', 'typescript', 'javascript',
    'postgresql', 'mysql', 'mongodb', 'aws', 'docker',
    'rest api', 'restful', 'websocket', 'langchain', 'langgraph',
    'rag', 'ollama', 'agentic ai', 'llm', 'generative ai',
    'vector search', 'vector database', 'fastapi', 'redis',
]

AI_KEYWORDS_LIST: list[str] = list(AI_KEYWORDS.keys())