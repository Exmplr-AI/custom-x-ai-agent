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
        .log-entry.action {
            border-left-color: #2196F3;
        }
        .log-entry.error {
            border-left-color: #f44336;
        }
        .log-entry.warning {
            border-left-color: #ff9800;
        }
        .log-entry.critical {
            border-left-color: #f44336;
            background: #3a2a2a;
        }
        .info { color: #4CAF50; }
        .error { color: #f44336; }
        .warning { color: #ff9800; }
        .critical { color: #f44336; font-weight: bold; }
        .action { color: #2196F3; }
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
        .extra {
            color: #888;
            font-size: 0.9em;
            margin-top: 4px;
            padding-top: 4px;
            border-top: 1px solid #3a3a3a;
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
            {% for log in logs %}
                <div class="log-entry {{ log.level.lower() }} {% if log.extra_fields and log.extra_fields.action %}action{% endif %}">
                    <span class="timestamp">{{ log.timestamp }}</span>
                    <span class="level">{{ log.level }}</span>
                    <span class="message">{{ log.message }}</span>
                    {% if log.extra_fields %}
                    <div class="extra">
                        {{ log.extra_fields | tojson(indent=2) }}
                    </div>
                    {% endif %}
                    {% if log.exception %}
                    <div class="extra error">
                        {{ log.exception }}
                    </div>
                    {% endif %}
                </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
'''

def parse_log_line(line):
    try:
        # Try to parse as JSON first
        return json.loads(line)
    except json.JSONDecodeError:
        # If not JSON, parse as regular log line
        match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^-]*)-\s*(\w+)\s*-\s*(.*)', line)
        if match:
            timestamp, level, message = match.groups()
            return {
                'timestamp': timestamp,
                'level': level,
                'message': message
            }
        return None

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
        
        # Create a log session first
        session_response = requests.post(
            'https://api.heroku.com/apps/custom-x-ai-agent/log-sessions',
            headers=headers,
            json={
                'dyno': 'worker.1',
                'lines': 50,  # Reduced from 100
                'tail': True,
                'source': 'app'
            },
            timeout=5  # Added timeout for session creation
        )
        
        logger.info(f"Session response status: {session_response.status_code}")
        
        if session_response.status_code != 201:
            error_msg = f"Error creating log session: {session_response.status_code}"
            try:
                error_details = session_response.text
                error_msg += f" - {error_details}"
            except:
                error_msg += f" - {session_response.text}"
            logger.error(error_msg)
            return [{'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'), 'level': 'ERROR', 'message': error_msg}], False
            
        # Get the logplex URL from the session
        session_data = session_response.json()
        logplex_url = session_data.get('logplex_url')
        
        if not logplex_url:
            logger.error("No logplex URL in session response")
            return [{'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'), 'level': 'ERROR', 'message': 'No logplex URL in session response'}], False
            
        logger.info(f"Fetching logs from logplex URL...")
        
        # Get the actual logs with shorter timeouts
        logs = []
        try:
            # Use a session for better connection reuse
            with requests.Session() as session:
                # Set shorter timeouts
                session.timeout = (2, 5)  # (connect timeout, read timeout)
                
                # Stream the response with a small chunk size
                with session.get(logplex_url, stream=True) as logs_response:
                    logs_response.raise_for_status()
                    
                    # Read fixed number of bytes instead of streaming indefinitely
                    content = logs_response.raw.read(16384)  # Read 16KB max
                    text = content.decode('utf-8')
                    
                    # Process the logs
                    for line in text.splitlines():
                        parsed = parse_log_line(line)
                        if parsed:
                            logs.append(parsed)
                            if len(logs) >= 50:  # Limit to 50 lines
                                break
                
        except requests.exceptions.ReadTimeout:
            # If we got any logs before timeout, use them
            if logs:
                logger.info("Got partial logs before timeout")
            else:
                logger.error("Timeout getting logs")
                return [{'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'), 'level': 'ERROR', 'message': 'Timeout getting logs. Please try again.'}], False
                
        logger.info(f"Retrieved {len(logs)} log lines")
        
        return logs if logs else [{'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'), 'level': 'INFO', 'message': 'No logs yet. Waiting for new entries...'}], False
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error getting logs: {str(e)}"
        logger.error(error_msg)
        return [{'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'), 'level': 'ERROR', 'message': error_msg}], False
    except Exception as e:
        error_msg = f"Error getting logs: {str(e)}"
        logger.error(error_msg)
        return [{'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'), 'level': 'ERROR', 'message': error_msg}], False

@app.route('/')
def show_logs():
    try:
        logs, setup_required = get_heroku_logs()
        return render_template_string(HTML_TEMPLATE, logs=logs, setup_required=setup_required)
    except Exception as e:
        logger.error(f"Error showing logs: {str(e)}")
        return render_template_string(HTML_TEMPLATE, 
            logs=[{'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'), 'level': 'ERROR', 'message': f'Error showing logs: {str(e)}'}], 
            setup_required=False
        )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("Web server starting up...")
    app.run(host='0.0.0.0', port=port)