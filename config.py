import os
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
CHAT_ID: str = os.getenv('CHAT_ID', '')
SEARCH_TERMS: list[str] = ['AI Engineer', 'Applied AI Engineer', 'Generative AI Engineer', 'LLM Engineer', 'Agentic AI Engineer', 'AI Full Stack Engineer', 'AI Software Engineer', 'Backend Engineer', 'Backend Developer', 'Python Developer', 'Python Backend Engineer', 'Software Engineer', 'Software Developer', 'SDE', 'SDE 1', 'Full Stack Engineer', 'Full Stack Developer', 'React Developer', 'Django Developer']
TARGET_ROLES: dict[str, list[str]] = {'highest': ['ai engineer', 'applied ai engineer', 'generative ai engineer', 'llm engineer', 'agentic ai engineer', 'ai full stack engineer', 'ai software engineer'], 'secondary': ['backend engineer', 'backend developer', 'python developer', 'python backend engineer', 'software engineer', 'software developer', 'sde', 'sde 1', 'sde1', 'sde-1'], 'additional': ['full stack engineer', 'full stack developer', 'react developer', 'django developer', 'ai application engineer', 'ai solutions engineer', 'ai platform engineer']}
SKILLS: list[str] = ['python', 'django', 'react', 'typescript', 'javascript', 'postgresql', 'mysql', 'mongodb', 'aws', 'docker', 'rest api', 'restful', 'websocket', 'langchain', 'langgraph', 'rag', 'ollama', 'agentic ai', 'llm', 'generative ai', 'vector search', 'vector database']
AI_KEYWORDS: list[str] = ['langchain', 'langgraph', 'agentic ai', 'rag', 'ollama', 'llm', 'generative ai', 'vector search', 'vector database', 'large language model', 'prompt engineering', 'ai agent']
BANNED_COMPANIES: list[str] = ['turing','Crossing Hurdles']
EXPERIENCE_MAX: int = 3
SCHEDULE_INTERVAL_HOURS: int = 2
NOTIFICATION_BATCH_SIZE: int = 10
MIN_SCORE_THRESHOLD: int = 15
MAX_PAGES_PER_SEARCH: int = 5
REQUEST_DELAY: tuple[float, float] = (2.0, 5.0)
PAGE_TIMEOUT: int = 30000
NAVIGATION_TIMEOUT: int = 30000
TARGET_LOCATIONS: list[str] = ['remote', 'india', 'bangalore', 'bengaluru', 'mumbai', 'delhi', 'ncr', 'hyderabad', 'pune', 'chennai', 'gurgaon', 'gurugram', 'noida', 'kolkata', 'work from home', 'wfh']
USER_AGENTS: list[str] = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0']
DATABASE_PATH: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jobs.db')
JOB_RETENTION_DAYS: int = 15
LOG_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
LOG_FILE: str = os.path.join(LOG_DIR, 'app.log')
LOG_MAX_BYTES: int = 5 * 1024 * 1024
LOG_BACKUP_COUNT: int = 3