from flask import Flask, render_template_string
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Use /tmp directory for logs in Heroku
LOG_FILE = '/tmp/app.log'
if not os.path.exists(LOG_FILE):
    open(LOG_FILE, 'a').close()
    logger.info("Created log file in /tmp")

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

@app.route('/')
def show_logs():
    try:
        # Read the last 100 lines of the log file
        with open(LOG_FILE, 'r') as f:
            logs = f.readlines()[-100:]
        
        if not logs:
            logs = ["No logs yet. Waiting for new entries..."]
            
        return render_template_string(HTML_TEMPLATE, logs=logs)
    except Exception as e:
        # Try to create log file again if it doesn't exist
        if not os.path.exists(LOG_FILE):
            open(LOG_FILE, 'a').close()
            logger.info("Log file created in /tmp")
            return render_template_string(HTML_TEMPLATE, logs=["Log file created. Waiting for entries..."])
        return render_template_string(HTML_TEMPLATE, logs=[f"Error with logs: {str(e)}"])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)