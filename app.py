from flask import Flask, render_template_string
import os
import logging
import sys
import requests
import time
import json
import re

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
            font-size: 14px;
            line-height: 1.5;
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
            height: 60px;  /* Increased from 48px by 25% */
            margin-right: 15px;
        }
        h1 {
            color: #4CAF50;
            margin: 0;
        }
        .log-entry {
            margin: 5px 0;
            padding: 8px 12px;
            border-left: 3px solid #4CAF50;
            background: #2a2a2a;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: 'Courier New', monospace;
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
        .timestamp {
            color: #888;
        }
        .level {
            color: #4CAF50;
            font-weight: bold;
        }
        .message {
            color: #e0e0e0;
        }
        .failed {
            color: #f44336;
        }
        .setup-note {
            margin: 20px 0;
            padding: 15px;
            background: #2a2a2a;
            border-left: 3px solid #ff9800;
            color: #ff9800;
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
        {% if setup_required %}
        <div class="setup-note">
            <strong>Setup Required:</strong> Please configure HEROKU_API_KEY in the environment variables to enable log viewing.
        </div>
        {% endif %}
        <div id="logs">
            {% for line in logs %}
                <div class="log-entry">{{ line | safe }}</div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
'''

def format_log_line(line):
    # Extract timestamp
    timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^:]*)', line)
    if timestamp_match:
        timestamp = timestamp_match.group(1)
        line = line.replace(timestamp, f'<span class="timestamp">{timestamp}</span>')
    
    # Format INFO/ERROR/WARNING levels
    line = re.sub(r'(INFO|ERROR|WARNING)', r'<span class="level">\1</span>', line)
    
    # Format failed messages
    if 'Failed' in line:
        line = re.sub(r'(Failed.*$)', r'<span class="failed">\1</span>', line)
    
    # Format HTTP status codes
    line = re.sub(r'(HTTP/[\d.]+ \d{3}.*)', r'<span class="info">\1</span>', line)
    
    return line

def get_heroku_logs():
    try:
        # Get Heroku API token from environment
        api_token = os.environ.get('HEROKU_API_KEY')
        if not api_token:
            logger.warning("HEROKU_API_KEY environment variable not set")
            return [], True  # Return empty logs and setup_required flag
            
        # Get logs from Heroku API
        headers = {
            'Accept': 'application/vnd.heroku+json; version=3',
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
        
        # Get logs directly from the API
        logs_response = requests.get(
            'https://api.heroku.com/apps/custom-x-ai-agent/log-sessions',
            headers=headers,
            params={
                'dyno': 'worker.1',
                'lines': 100,
                'tail': True,
                'source': 'app'
            }
        )
        
        if logs_response.status_code != 200:
            error_msg = f"Error getting logs: {logs_response.status_code}"
            try:
                error_details = logs_response.text
                error_msg += f" - {error_details}"
            except:
                error_msg += f" - {logs_response.text}"
            logger.error(error_msg)
            return [error_msg], False
            
        # Parse and return logs
        logs = []
        try:
            log_data = logs_response.json()
            if isinstance(log_data, list):
                for line in log_data:
                    if 'worker.1' in str(line) or 'INFO' in str(line):
                        logs.append(format_log_line(str(line)))
                        if len(logs) >= 100:  # Limit to 100 lines
                            break
            else:
                logger.error(f"Unexpected log data format: {log_data}")
                return ["Error: Unexpected log data format"], False
        except Exception as e:
            logger.error(f"Error parsing log data: {str(e)}")
            return [f"Error parsing log data: {str(e)}"], False
                
        logger.info(f"Retrieved {len(logs)} log lines")
        
        return logs if logs else ["No logs yet. Waiting for new entries..."], False
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error getting logs: {str(e)}"
        logger.error(error_msg)
        return [error_msg], False
    except Exception as e:
        error_msg = f"Error getting logs: {str(e)}"
        logger.error(error_msg)
        return [error_msg], False

@app.route('/')
def show_logs():
    try:
        logs, setup_required = get_heroku_logs()
        return render_template_string(HTML_TEMPLATE, logs=logs, setup_required=setup_required)
    except Exception as e:
        logger.error(f"Error showing logs: {str(e)}")
        return render_template_string(HTML_TEMPLATE, logs=[f"Error showing logs: {str(e)}"], setup_required=False)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("Web server starting up...")
    app.run(host='0.0.0.0', port=port)