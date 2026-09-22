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
    'Software Engineer',
    'Frontend Developer',
    'Backend Engineer',
    'Full Stack Developer',
    'React Developer',
    'Node.js Developer',
    'Application Support',
    'AI Engineer',
    'Python Developer',
]

# ─────────────────────────────────────────────────────────────────────────────
# WELLFOUND-SPECIFIC SEARCH TERMS
# ─────────────────────────────────────────────────────────────────────────────
WELLFOUND_SEARCH_TERMS: list[str] = [
    'software-engineer',
    'frontend-engineer',
    'backend-engineer',
    'full-stack-engineer',
    'react-developer',
    'node-js-developer',
    'ai-engineer',
    'application-support',
    'python-developer',
]

# ─────────────────────────────────────────────────────────────────────────────
# TARGET ROLES
# ─────────────────────────────────────────────────────────────────────────────
TARGET_ROLES = {
    "primary": [
        "Software Engineer", "Software Developer", "Software Development Engineer",
        "SDE", "Associate Software Engineer", "Junior Software Engineer",
        "Junior Software Developer", "Software Engineer I", "Software Developer I",
        "Graduate Software Engineer", "Graduate Software Developer",
        
        "Frontend Engineer", "Frontend Developer", "Front-End Engineer",
        "Front-End Developer", "React Developer", "React.js Developer",
        "React Engineer", "Next.js Developer", "Next.js Engineer",
        "UI Engineer", "UI Developer", "Web Developer", "Web Engineer",
        "Web Application Developer", "Web Application Engineer",
        "JavaScript Developer", "TypeScript Developer",

        "Full Stack Developer", "Full Stack Engineer", "Fullstack Developer",
        "Fullstack Engineer", "Full-Stack Developer", "Full-Stack Engineer",
        "MERN Developer", "MERN Stack Developer", "MERN Engineer", "MERN Stack Engineer",

        "Backend Developer", "Backend Engineer", "Back-End Developer",
        "Back-End Engineer", "Node.js Developer", "Node.js Engineer",
        "Node Developer", "API Developer", "API Engineer", "REST API Developer",
        "Backend Software Engineer",

        "Product Engineer", "Product Developer", "Platform Engineer",
        "Application Engineer", "Application Developer", "Software Application Engineer",
    ],
    "ai": [
        "AI Engineer", "AI Software Engineer", "AI Developer",
        "AI Application Engineer", "AI Application Developer",
        "AI Integration Engineer", "AI Integration Developer",
        "Generative AI Engineer", "Generative AI Developer",
        "GenAI Engineer", "GenAI Developer", "LLM Engineer",
        "LLM Developer", "AI Software Developer", "AI Engineer - Software",
    ],
    "support": [
        "Application Support Engineer", "Application Support Analyst",
        "Application Support Developer", "Software Support Engineer",
        "Software Support Analyst", "Production Support Engineer",
        "Production Support Analyst", "Technical Support Engineer",
        "Technical Application Support Engineer",
    ],
    "secondary": [
        "Cloud Engineer", "AWS Engineer", "DevOps Engineer",
        "DevOps Developer", "Cloud Software Engineer",
        "Database Developer", "Database Engineer", "MongoDB Developer",
        "Node.js Backend Developer", "API Integration Engineer",
    ],
}

TARGET_ROLE_SCORES = {
    'ai': 120,
    'primary': 120,
    'secondary': 120,
    'support': 120
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
    'role': 0.50,          # Boosted so a matching role guarantees a pass
    'experience': 0.15,    # Boosted to reward matching experience
    'ai': 0.10,
    'skill': 0.10,
    'responsibility': 0.10,
    'location': 0.05,
}

# ─────────────────────────────────────────────────────────────────────────────
# MATCH BANDS
# ─────────────────────────────────────────────────────────────────────────────
MATCH_BANDS: dict[str, int] = {
    'EXCELLENT': 90,
    'STRONG': 80,
    'GOOD': 55,
    'BORDERLINE': 0,
    # Below 40 = SKIP
}

# Only notify these bands via Telegram
NOTIFY_BANDS: list[str] = ['EXCELLENT', 'STRONG', 'GOOD', 'BORDERLINE']

# Minimum final score (0-100) to save and notify
MIN_SCORE_THRESHOLD: int = 0

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