from flask import Flask, render_template_string, send_file
import os
import logging
import sys
import requests

app = Flask(__name__)

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
            <img src="/logo" alt="EXMPLR Logo" class="logo">
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
        # Get Heroku API token from environment
        api_token = os.environ.get('HEROKU_API_KEY')
        if not api_token:
            return ["Error: HEROKU_API_KEY not set"]
            
        # Get logs from Heroku API
        headers = {
            'Accept': 'application/vnd.heroku+json; version=3',
            'Authorization': f'Bearer {api_token}'
        }
        
        response = requests.get(
            'https://api.heroku.com/apps/custom-x-ai-agent/log-sessions',
            headers=headers,
            params={'tail': True, 'lines': 100}
        )
        
        if response.status_code != 200:
            return [f"Error getting logs: {response.status_code}"]
            
        # Parse and return logs
        logs = []
        for line in response.text.splitlines():
            if 'worker.1' in line or 'INFO' in line:
                logs.append(line)
        
        return logs if logs else ["No logs yet. Waiting for new entries..."]
        
    except Exception as e:
        logger.error(f"Error getting logs: {str(e)}")
        return [f"Error getting logs: {str(e)}"]

@app.route('/logo')
def serve_logo():
    return send_file('Exmplr logo white.png')

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