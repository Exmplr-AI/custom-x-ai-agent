from flask import Flask, render_template_string
import os
import logging
import sys

app = Flask(__name__)

# Configure logging to stdout for Heroku
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>$EXMPLR Agent Logs</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body {
            background: #1a1a1a;
            color: #e0e0e0;
            font-family: monospace;
            padding: 20px;
            margin: 0;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #4CAF50;
            border-bottom: 1px solid #4CAF50;
            padding-bottom: 10px;
        }
        .log-entry {
            margin: 5px 0;
            padding: 5px;
            border-left: 3px solid #4CAF50;
            background: #2a2a2a;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .info { color: #4CAF50; }
        .error { color: #f44336; }
        .warning { color: #ff9800; }
        .refresh-note {
            position: fixed;
            top: 10px;
            right: 10px;
            background: #333;
            padding: 5px 10px;
            border-radius: 3px;
            font-size: 0.8em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>$EXMPLR Agent Logs</h1>
        <div class="refresh-note">Auto-refreshes every 30 seconds</div>
        <div id="logs">
            {% for line in logs %}
                <div class="log-entry {% if 'ERROR' in line %}error{% elif 'WARNING' in line %}warning{% else %}info{% endif %}">
                    {{ line }}
                </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
'''

# Store logs in memory
log_buffer = []
MAX_LOGS = 100

class MemoryHandler(logging.Handler):
    def emit(self, record):
        global log_buffer
        log_buffer.append(self.format(record))
        if len(log_buffer) > MAX_LOGS:
            log_buffer = log_buffer[-MAX_LOGS:]

# Add memory handler
memory_handler = MemoryHandler()
memory_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(memory_handler)

@app.route('/')
def show_logs():
    try:
        if not log_buffer:
            log_buffer.append("No logs yet. Waiting for new entries...")
            
        return render_template_string(HTML_TEMPLATE, logs=log_buffer)
    except Exception as e:
        logger.error(f"Error showing logs: {str(e)}")
        return render_template_string(HTML_TEMPLATE, logs=[f"Error showing logs: {str(e)}"])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("Web server starting up...")
    app.run(host='0.0.0.0', port=port)