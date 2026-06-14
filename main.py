import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scheduler.scheduler import start_scheduler

def main():
    print('\n    +==================================================+\n    |         Job Hunter System v1.0                    |\n    |         Resume-Driven Job Scraper                 |\n    |                                                   |\n    |  Sources: Wellfound | Indeed | Naukri | Cutshort  |\n    |  Notifications: Telegram                          |\n    |                                                   |\n    |  Press Ctrl+C to stop                             |\n    +==================================================+\n    ')
    try:
        asyncio.run(start_scheduler())
    except KeyboardInterrupt:
        print('\nGoodbye!')
    except Exception as e:
        print(f'\nFatal error: {e}')
        sys.exit(1)
if __name__ == '__main__':
    main()