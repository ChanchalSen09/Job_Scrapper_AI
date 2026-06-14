import asyncio
import sys
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scheduler.scheduler import start_scheduler

# Dummy server to satisfy Render's Web Service port binding requirement
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Job Hunter Bot is running!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

def main():
    print('\n    +==================================================+\n    |         Job Hunter System v1.0                    |\n    |         Resume-Driven Job Scraper                 |\n    |                                                   |\n    |  Sources: Wellfound | Indeed | Naukri | Cutshort  |\n    |  Notifications: Telegram                          |\n    |                                                   |\n    |  Press Ctrl+C to stop                             |\n    +==================================================+\n    ')
    
    # Start the dummy web server in a background thread if PORT is set (like on Render)
    if os.environ.get("RENDER") or os.environ.get("PORT"):
        threading.Thread(target=run_dummy_server, daemon=True).start()
        print("Started dummy web server for Render Web Service compatibility.")

    try:
        asyncio.run(start_scheduler())
    except KeyboardInterrupt:
        print('\nGoodbye!')
    except Exception as e:
        print(f'\nFatal error: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()