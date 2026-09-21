"""
Send a realistic test notification to the Telegram group.

Sends 3 sample jobs (one per band: EXCELLENT, STRONG, GOOD) so you can
verify the full notification format looks correct in your Telegram group.

Usage:
    python test_telegram.py
"""
import asyncio
import sys, os
sys.stdout.reconfigure(encoding='utf-8')  # Fix Windows cp1252 console
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram_bot.notifier import TelegramNotifier
from utils.logger import get_logger

logger = get_logger('test_telegram')

SAMPLE_JOBS = [
    {
        'title': 'Generative AI Engineer',
        'company': 'NexusAI Labs (TEST)',
        'location': 'Remote, India',
        'url': 'https://linkedin.com/jobs/view/test-genai-engineer',
        'source': 'linkedin',
        'final_score': 92,
        'score': 92,
        'match_band': 'EXCELLENT',
        'role_category': 'GENAI',
        'work_type': 'remote',
        'posted_date': '1 day ago',
        'freshness_score': 1,
        'matched_skills': ['python', 'fastapi', 'langchain', 'rag', 'openai api', 'postgresql', 'langgraph'],
        'missing_required_skills': [],
        'experience_requirement': {'min': 1, 'max': 3, 'is_range': True, 'is_required': True, 'freshers_welcome': False},
        'match_reason': 'EXCELLENT match: Generative AI Engineer | Python + Fastapi + Langchain + Rag | Experience: 1–3 years | Location: Remote',
        'rejection_reason': None,
        'is_rejected': False,
        'description': 'Build GenAI applications using Python, FastAPI, LangChain, OpenAI API.',
    },
    {
        'title': 'AI Backend Engineer',
        'company': 'DataMind Technologies (TEST)',
        'location': 'Bangalore, India (Hybrid)',
        'url': 'https://naukri.com/job-listings/test-ai-backend',
        'source': 'naukri',
        'final_score': 84,
        'score': 84,
        'match_band': 'STRONG',
        'role_category': 'AI_BACKEND',
        'work_type': 'hybrid',
        'posted_date': '2 days ago',
        'freshness_score': 2,
        'matched_skills': ['python', 'fastapi', 'llm apis', 'rag', 'postgresql', 'redis'],
        'missing_required_skills': [],
        'experience_requirement': {'min': 1, 'max': 2, 'is_range': True, 'is_required': True, 'freshers_welcome': False},
        'match_reason': 'STRONG match: AI Backend Engineer | Python + Fastapi + Rag + Redis | Experience: 1–2 years | Location: Hybrid',
        'rejection_reason': None,
        'is_rejected': False,
        'description': 'Build AI backend services using Python, FastAPI, LLM APIs, RAG pipelines.',
    },
    {
        'title': 'Full Stack AI Engineer',
        'company': 'Stealth AI Startup (TEST)',
        'location': 'Remote — India',
        'url': 'https://wellfound.com/company/stealth-ai/jobs/full-stack-test',
        'source': 'wellfound',
        'final_score': 75,
        'score': 75,
        'match_band': 'GOOD',
        'role_category': 'AI_FULL_STACK',
        'work_type': 'remote',
        'posted_date': '3 days ago',
        'freshness_score': 3,
        'matched_skills': ['python', 'react', 'typescript', 'langchain', 'vector search'],
        'missing_required_skills': [],
        'experience_requirement': {'min': None, 'max': None, 'freshers_welcome': True},
        'match_reason': 'GOOD match: Full Stack AI Engineer | Python + React + Langchain | Experience: Freshers welcome | Location: Remote',
        'rejection_reason': None,
        'is_rejected': False,
        'description': 'Full-stack AI product engineer at early-stage startup.',
    },
]


async def main():
    print("\nSending test notification to Telegram group...")
    print("   3 sample jobs: EXCELLENT / STRONG / GOOD")
    print("   Check your Telegram group now!\n")

    notifier = TelegramNotifier()

    # First send alive ping
    ok = await notifier.send_test_message()
    if not ok:
        print("FAILED to send test message. Check BOT_TOKEN and CHAT_ID in .env")
        return

    print("Alive ping sent -- sending 3 sample job notifications...")
    await asyncio.sleep(1)

    await notifier.send_jobs(SAMPLE_JOBS)

    print("\nDone! Check your Telegram group.")
    print("   If you see the jobs -- the system is ready to run.\n")


if __name__ == '__main__':
    asyncio.run(main())
