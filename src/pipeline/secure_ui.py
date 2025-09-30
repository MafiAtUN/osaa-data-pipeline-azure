"""Secure web interface for OSAA MVP.

This module provides a password-protected web interface with authentication,
session management, and security features.
"""

import os
import logging
from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify, make_response
from werkzeug.exceptions import Unauthorized, Forbidden
import uuid

from pipeline.auth import (
    authenticate_user, validate_session, logout_user, 
    get_security_status, cleanup_expired_sessions,
    AuthenticationError, AuthorizationError
)

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', str(uuid.uuid4()))

# Security headers
@app.after_request
def after_request(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    return response

def get_client_ip():
    """Get client IP address."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def require_login(f):
    """Decorator to require login for routes."""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('auth_token')
        if not token:
            return redirect(url_for('login'))
        
        user_info = validate_session(token, get_client_ip())
        if not user_info:
            response = make_response(redirect(url_for('login')))
            response.set_cookie('auth_token', '', expires=0)
            return response
        
        # Update session last activity
        request.user_info = user_info
        return f(*args, **kwargs)
    
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            return render_template_string(LOGIN_TEMPLATE, error="Username and password are required")
        
        try:
            token = authenticate_user(username, password, get_client_ip())
            response = make_response(redirect(url_for('dashboard')))
            response.set_cookie('auth_token', token, httponly=True, secure=True, samesite='Strict')
            return response
        
        except AuthenticationError as e:
            logger.warning(f"Failed login attempt for {username} from {get_client_ip()}: {e}")
            return render_template_string(LOGIN_TEMPLATE, error=str(e))
        
        except Exception as e:
            logger.error(f"Login error: {e}")
            return render_template_string(LOGIN_TEMPLATE, error="An error occurred during login")
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    """Logout and clear session."""
    token = request.cookies.get('auth_token')
    if token:
        try:
            user_info = validate_session(token, get_client_ip())
            if user_info:
                logout_user(user_info['session_id'])
                logger.info(f"User {user_info['username']} logged out")
        except Exception as e:
            logger.error(f"Logout error: {e}")
    
    response = make_response(redirect(url_for('login')))
    response.set_cookie('auth_token', '', expires=0)
    return response

@app.route('/')
@require_login
def dashboard():
    """Main dashboard."""
    return render_template_string(DASHBOARD_TEMPLATE, user=request.user_info)

@app.route('/pipeline')
@require_login
def pipeline():
    """Pipeline management interface."""
    return render_template_string(PIPELINE_TEMPLATE, user=request.user_info)

@app.route('/security')
@require_login
def security():
    """Security status and monitoring."""
    security_status = get_security_status()
    return render_template_string(SECURITY_TEMPLATE, user=request.user_info, status=security_status)

@app.route('/api/run-pipeline', methods=['POST'])
@require_login
def run_pipeline():
    """API endpoint to run pipeline operations."""
    try:
        operation = request.json.get('operation')
        if not operation:
            return jsonify({'error': 'Operation is required'}), 400
        
        # Validate operation
        allowed_operations = ['ingest', 'transform', 'etl', 'promote', 'config_test']
        if operation not in allowed_operations:
            return jsonify({'error': 'Invalid operation'}), 400
        
        # Here you would execute the actual pipeline operation
        # For now, we'll just return a success message
        logger.info(f"User {request.user_info['username']} requested operation: {operation}")
        
        return jsonify({
            'success': True,
            'message': f'Pipeline operation "{operation}" initiated',
            'operation': operation,
            'timestamp': str(datetime.utcnow())
        })
    
    except Exception as e:
        logger.error(f"Pipeline execution error: {e}")
        return jsonify({'error': 'Pipeline execution failed'}), 500

# HTML Templates
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OSAA MVP - Login</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 0; }
        .container { max-width: 400px; margin: 100px auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; color: #555; }
        input[type="text"], input[type="password"] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #007cba; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #005a87; }
        .error { color: #d32f2f; background: #ffebee; padding: 10px; border-radius: 4px; margin-bottom: 20px; }
        .security-info { margin-top: 20px; padding: 15px; background: #e3f2fd; border-radius: 4px; font-size: 14px; color: #1976d2; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 OSAA MVP Access</h1>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Login</button>
        </form>
        <div class="security-info">
            <strong>Security Notice:</strong> This is a secure UN application. 
            All access is logged and monitored. Unauthorized access is prohibited.
        </div>
    </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OSAA MVP - Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 0; }
        .header { background: #1976d2; color: white; padding: 20px; }
        .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
        .nav { background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .nav a { margin-right: 20px; text-decoration: none; color: #1976d2; font-weight: bold; }
        .nav a:hover { text-decoration: underline; }
        .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .user-info { float: right; color: white; }
        .logout { color: #ffcdd2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>OSAA MVP Dashboard</h1>
        <div class="user-info">
            Welcome, {{ user.username }} | 
            <a href="/logout" class="logout">Logout</a>
        </div>
    </div>
    <div class="container">
        <div class="nav">
            <a href="/">Dashboard</a>
            <a href="/pipeline">Pipeline</a>
            <a href="/security">Security</a>
        </div>
        
        <div class="card">
            <h2>Welcome to OSAA MVP</h2>
            <p>This is the secure dashboard for the United Nations Office of the Special Adviser on Africa data pipeline.</p>
            <p>Use the navigation menu to access different features.</p>
        </div>
        
        <div class="card">
            <h3>Quick Actions</h3>
            <button onclick="runPipeline('config_test')">Test Configuration</button>
            <button onclick="runPipeline('ingest')">Run Data Ingestion</button>
            <button onclick="runPipeline('etl')">Run ETL Pipeline</button>
            <button onclick="runPipeline('promote')">Promote to Production</button>
        </div>
        
        <div class="card">
            <h3>Security Information</h3>
            <p>✅ Session: Active</p>
            <p>✅ IP Address: {{ request.remote_addr }}</p>
            <p>✅ Last Login: {{ user.expires_at }}</p>
        </div>
    </div>
    
    <script>
        async function runPipeline(operation) {
            try {
                const response = await fetch('/api/run-pipeline', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ operation: operation })
                });
                const result = await response.json();
                alert(result.message || result.error);
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }
    </script>
</body>
</html>
"""

PIPELINE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OSAA MVP - Pipeline Management</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 0; }
        .header { background: #1976d2; color: white; padding: 20px; }
        .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
        .nav { background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .nav a { margin-right: 20px; text-decoration: none; color: #1976d2; font-weight: bold; }
        .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .pipeline-op { margin: 10px 0; padding: 15px; border: 1px solid #ddd; border-radius: 4px; }
        button { padding: 10px 20px; background: #007cba; color: white; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        button:hover { background: #005a87; }
        .danger { background: #d32f2f; }
        .danger:hover { background: #b71c1c; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Pipeline Management</h1>
        <div class="user-info">
            Welcome, {{ user.username }} | 
            <a href="/logout" class="logout">Logout</a>
        </div>
    </div>
    <div class="container">
        <div class="nav">
            <a href="/">Dashboard</a>
            <a href="/pipeline">Pipeline</a>
            <a href="/security">Security</a>
        </div>
        
        <div class="card">
            <h2>Data Pipeline Operations</h2>
            <p>Select an operation to execute:</p>
            
            <div class="pipeline-op">
                <h3>Configuration Test</h3>
                <p>Test Azure connectivity and configuration</p>
                <button onclick="runPipeline('config_test')">Run Test</button>
            </div>
            
            <div class="pipeline-op">
                <h3>Data Ingestion</h3>
                <p>Convert CSV files to Parquet and upload to Azure Blob Storage</p>
                <button onclick="runPipeline('ingest')">Run Ingestion</button>
            </div>
            
            <div class="pipeline-op">
                <h3>Data Transformation</h3>
                <p>Run SQLMesh transformations on the data</p>
                <button onclick="runPipeline('transform')">Run Transform</button>
            </div>
            
            <div class="pipeline-op">
                <h3>ETL Pipeline</h3>
                <p>Run complete Extract-Transform-Load process</p>
                <button onclick="runPipeline('etl')">Run ETL</button>
            </div>
            
            <div class="pipeline-op">
                <h3>Data Promotion</h3>
                <p>Promote data from development to production</p>
                <button onclick="runPipeline('promote')" class="danger">Promote to Production</button>
            </div>
        </div>
    </div>
    
    <script>
        async function runPipeline(operation) {
            if (confirm(`Are you sure you want to run: ${operation}?`)) {
                try {
                    const response = await fetch('/api/run-pipeline', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ operation: operation })
                    });
                    const result = await response.json();
                    alert(result.message || result.error);
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }
        }
    </script>
</body>
</html>
"""

SECURITY_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OSAA MVP - Security</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 0; }
        .header { background: #1976d2; color: white; padding: 20px; }
        .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
        .nav { background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .nav a { margin-right: 20px; text-decoration: none; color: #1976d2; font-weight: bold; }
        .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-item { padding: 10px; margin: 5px 0; border-left: 4px solid #4caf50; background: #f1f8e9; }
        .warning { border-left-color: #ff9800; background: #fff3e0; }
        .danger { border-left-color: #f44336; background: #ffebee; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Security Dashboard</h1>
        <div class="user-info">
            Welcome, {{ user.username }} | 
            <a href="/logout" class="logout">Logout</a>
        </div>
    </div>
    <div class="container">
        <div class="nav">
            <a href="/">Dashboard</a>
            <a href="/pipeline">Pipeline</a>
            <a href="/security">Security</a>
        </div>
        
        <div class="card">
            <h2>Security Status</h2>
            
            <div class="status-item">
                <strong>Active Sessions:</strong> {{ status.active_sessions }}
            </div>
            
            <div class="status-item">
                <strong>Total Sessions:</strong> {{ status.total_sessions }}
            </div>
            
            <div class="status-item {% if status.failed_login_attempts > 0 %}warning{% endif %}">
                <strong>Failed Login Attempts:</strong> {{ status.failed_login_attempts }}
            </div>
            
            <div class="status-item {% if status.locked_accounts > 0 %}danger{% endif %}">
                <strong>Locked Accounts:</strong> {{ status.locked_accounts }}
            </div>
            
            <div class="status-item">
                <strong>Session Timeout:</strong> {{ status.session_timeout_minutes }} minutes
            </div>
            
            <div class="status-item">
                <strong>Max Login Attempts:</strong> {{ status.max_login_attempts }}
            </div>
            
            <div class="status-item">
                <strong>Lockout Duration:</strong> {{ status.lockout_duration_minutes }} minutes
            </div>
        </div>
        
        <div class="card">
            <h2>Security Features</h2>
            <ul>
                <li>✅ Password-based authentication</li>
                <li>✅ Session management with JWT tokens</li>
                <li>✅ IP address validation</li>
                <li>✅ Login attempt limiting</li>
                <li>✅ Account lockout protection</li>
                <li>✅ Secure HTTP headers</li>
                <li>✅ HTTPS enforcement</li>
                <li>✅ Activity logging and monitoring</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""

if __name__ == '__main__':
    # Cleanup expired sessions periodically
    import threading
    import time
    
    def cleanup_sessions():
        while True:
            time.sleep(300)  # Cleanup every 5 minutes
            cleanup_expired_sessions()
    
    cleanup_thread = threading.Thread(target=cleanup_sessions, daemon=True)
    cleanup_thread.start()
    
    # Run the secure web interface
    app.run(host='0.0.0.0', port=8080, debug=False)
