import asyncio
import sys
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scheduler.scheduler import start_scheduler

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Hunter Dashboard</title>
    <style>
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container {
            background: #1e293b;
            padding: 3rem;
            border-radius: 16px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            text-align: center;
            max-width: 400px;
        }
        h1 { margin-top: 0; font-size: 1.5rem; color: #38bdf8; }
        p { color: #94a3b8; margin-bottom: 2rem; line-height: 1.5; }
        .btn {
            background: linear-gradient(135deg, #0ea5e9, #3b82f6);
            color: white;
            border: none;
            padding: 1rem 2rem;
            font-size: 1.1rem;
            font-weight: 600;
            border-radius: 9999px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5);
        }
        .btn:active {
            transform: translateY(0);
        }
        .status { margin-top: 1.5rem; font-size: 0.9rem; min-height: 1.5rem; }
        .success { color: #34d399; }
        .error { color: #f87171; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Job Hunter System</h1>
        <p>Your automated resume-driven job scraper is running in the background.</p>
        <button class="btn" id="triggerBtn" onclick="triggerScraper()">
            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            Trigger Scraper Now
        </button>
        <div class="status" id="statusMessage"></div>
    </div>

    <script>
        async function triggerScraper() {
            const btn = document.getElementById('triggerBtn');
            const status = document.getElementById('statusMessage');
            
            btn.disabled = true;
            btn.style.opacity = '0.7';
            status.className = 'status';
            status.innerText = 'Triggering...';

            try {
                const response = await fetch('/trigger', { method: 'POST' });
                if (response.ok) {
                    status.className = 'status success';
                    status.innerText = 'Scraper triggered successfully! Check logs.';
                } else {
                    const data = await response.json();
                    status.className = 'status error';
                    status.innerText = 'Failed: ' + (data.message || 'Unknown error');
                }
            } catch (err) {
                status.className = 'status error';
                status.innerText = 'Error connecting to server: ' + String(err);
            } finally {
                setTimeout(() => {
                    btn.disabled = false;
                    btn.style.opacity = '1';
                }, 2000);
            }
        }
    </script>
</body>
</html>
"""

# Server to provide a UI and satisfy Render's Web Service port binding requirement
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode('utf-8'))
        
    def do_POST(self):
        if self.path == '/trigger':
            try:
                import scheduler.scheduler as sch
                if getattr(sch, 'GLOBAL_SCHEDULER', None):
                    import time
                    # We use trigger='date' without run_date to run immediately
                    sch.GLOBAL_SCHEDULER.add_job(
                        sch.run_pipeline, 
                        trigger='date', 
                        id=f'manual_run_{int(time.time())}'
                    )
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"status": "success"}')
                else:
                    self.send_response(500)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"status": "error", "message": "Scheduler not initialized"}')
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                err_msg = str(e).replace('"', "'")
                self.wfile.write(f'{{"status": "error", "message": "{err_msg}" }}'.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

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