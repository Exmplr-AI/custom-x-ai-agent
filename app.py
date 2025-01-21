from flask import Flask, render_template_string, send_from_directory
import os
import logging
import sys
import subprocess

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Configure logging
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
        .header {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
            border-bottom: 1px solid #4CAF50;
            padding-bottom: 10px;
        }
        .logo {
            height: 40px;
            margin-right: 15px;
        }
        h1 {
            color: #4CAF50;
            margin: 0;
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
        <div class="header">
            <img src="{{ url_for('static', filename='exmplr_logo_white.png') }}" alt="EXMPLR Logo" class="logo">
            <h1>Agent Logs</h1>
        </div>
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

def get_heroku_logs():
    try:
        # Get logs using heroku CLI
        result = subprocess.run(
            ['heroku', 'logs', '--app', 'custom-x-ai-agent', '--num', '100'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse and return logs
        logs = []
        for line in result.stdout.splitlines():
            if 'worker.1' in line or 'INFO' in line:
                logs.append(line)
        
        return logs if logs else ["No logs yet. Waiting for new entries..."]
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting logs: {str(e)}")
        return [f"Error getting logs: {str(e)}"]
    except Exception as e:
        logger.error(f"Error getting logs: {str(e)}")
        return [f"Error getting logs: {str(e)}"]

@app.route('/')
def show_logs():
    try:
        logs = get_heroku_logs()
        return render_template_string(HTML_TEMPLATE, logs=logs)
    except Exception as e:
        logger.error(f"Error showing logs: {str(e)}")
        return render_template_string(HTML_TEMPLATE, logs=[f"Error showing logs: {str(e)}"])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("Web server starting up...")
    app.run(host='0.0.0.0', port=port)