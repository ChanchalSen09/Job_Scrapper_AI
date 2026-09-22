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
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --glass-bg: rgba(20, 27, 45, 0.6);
            --glass-border: rgba(255, 255, 255, 0.08);
            --accent-glow: rgba(56, 189, 248, 0.4);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }
        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(circle at 15% 50%, rgba(56, 189, 248, 0.12), transparent 25%),
                radial-gradient(circle at 85% 30%, rgba(139, 92, 246, 0.12), transparent 25%);
            color: var(--text-main);
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            overflow: hidden;
        }
        .dashboard-card {
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            padding: 3.5rem 3rem;
            border-radius: 24px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1);
            text-align: center;
            max-width: 420px;
            width: 100%;
            position: relative;
        }
        .dashboard-card::before {
            content: '';
            position: absolute;
            top: -1px; left: 10%; right: 10%;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(56, 189, 248, 0.8), transparent);
            opacity: 0.5;
        }
        h1 { 
            margin: 0 0 0.5rem 0; 
            font-size: 2rem; 
            font-weight: 800;
            background: linear-gradient(135deg, #f8fafc, #38bdf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }
        p { 
            color: var(--text-muted); 
            margin-bottom: 2.5rem; 
            line-height: 1.6; 
            font-size: 1.05rem;
            font-weight: 300;
        }
        .btn-trigger {
            background: linear-gradient(135deg, #0ea5e9, #6366f1);
            color: white;
            border: none;
            padding: 1rem 2.5rem;
            font-size: 1.1rem;
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.75rem;
            width: 100%;
            position: relative;
            overflow: hidden;
        }
        .btn-trigger::after {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(135deg, rgba(255,255,255,0.2), transparent);
            opacity: 0;
            transition: opacity 0.3s;
        }
        .btn-trigger:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px var(--accent-glow);
        }
        .btn-trigger:hover::after {
            opacity: 1;
        }
        .btn-trigger:active {
            transform: translateY(1px);
            box-shadow: 0 5px 10px rgba(56, 189, 248, 0.2);
        }
        .btn-trigger:disabled {
            background: #334155;
            box-shadow: none;
            transform: none;
            cursor: not-allowed;
            color: #94a3b8;
        }
        .status-container {
            margin-top: 2rem;
            min-height: 24px;
            font-size: 0.95rem;
            font-weight: 400;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            transition: all 0.3s ease;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #3b82f6;
            display: none;
        }
        .status-dot.pulsing {
            display: block;
            animation: pulse 1.5s infinite;
        }
        .success { color: #34d399; }
        .error { color: #f87171; }
        .neutral { color: var(--text-muted); }
        
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(59, 130, 246, 0); }
            100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
        }
    </style>
</head>
<body>
    <div class="dashboard-card">
        <h1>Job Hunter System</h1>
        <p>Automated resume-driven scraper is monitoring in the background.</p>
        
        <button class="btn-trigger" id="triggerBtn" onclick="triggerScraper()">
            <svg width="22" height="22" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Trigger Scraper Now
        </button>
        
        <div class="status-container">
            <div class="status-dot" id="statusDot"></div>
            <span id="statusText" class="neutral">System idle</span>
        </div>
    </div>

    <script>
        async function triggerScraper() {
            const btn = document.getElementById('triggerBtn');
            const statusText = document.getElementById('statusText');
            const statusDot = document.getElementById('statusDot');
            
            btn.disabled = true;
            statusDot.className = 'status-dot pulsing';
            statusText.className = 'neutral';
            statusText.innerText = 'Triggering background pipeline...';

            try {
                const response = await fetch('/trigger', { method: 'POST' });
                if (response.ok) {
                    statusDot.style.display = 'none';
                    statusText.className = 'success';
                    statusText.innerText = 'Pipeline triggered successfully!';
                } else {
                    const data = await response.json();
                    statusDot.style.display = 'none';
                    statusText.className = 'error';
                    statusText.innerText = 'Failed: ' + (data.message || 'Unknown error');
                }
            } catch (err) {
                statusDot.style.display = 'none';
                statusText.className = 'error';
                statusText.innerText = 'Connection error. Check logs.';
            } finally {
                setTimeout(() => {
                    btn.disabled = false;
                    statusText.innerText = 'System idle';
                    statusText.className = 'neutral';
                    statusDot.style.display = 'none';
                }, 4000);
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
    
    # Start the web UI server in a background thread
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Started local web dashboard at http://localhost:8080")

    try:
        asyncio.run(start_scheduler())
    except KeyboardInterrupt:
        print('\nGoodbye!')
    except Exception as e:
        print(f'\nFatal error: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()