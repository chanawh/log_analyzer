import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, Response, request, jsonify, send_file, session
from core.ssh_browser import SSHBrowser

app = Flask(__name__)
app.secret_key = 'supersecret' # Needed for session management

# Store browser instances per session
ssh_sessions = {}

def get_browser():
    sid = session.get('sid')
    if sid and sid in ssh_sessions:
        return ssh_sessions[sid]
    return None

@app.route('/ssh/connect', methods=['POST'])
def connect_ssh():
    data = request.json
    host = data.get('host')
    username = data.get('username')
    password = data.get('password')
    if not host or not username or not password:
        return jsonify({'error': 'Missing credentials'}), 400
    browser = SSHBrowser()
    try:
        browser.connect(host, username, password)
        sid = os.urandom(16).hex()
        ssh_sessions[sid] = browser
        session['sid'] = sid
        return jsonify({'message': 'Connected', 'current_path': browser.current_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ssh/list', methods=['GET'])
def list_dir():
    browser = get_browser()
    if not browser:
        return jsonify({'error': 'Not connected'}), 401
    path = request.args.get('path', browser.current_path)
    items = browser.list_dir(path)
    return jsonify({'items': [{'name': n, 'is_dir': d} for n, d in items]})

@app.route('/ssh/change', methods=['POST'])
def change_dir():
    browser = get_browser()
    if not browser:
        return jsonify({'error': 'Not connected'}), 401
    data = request.json
    subdir = data.get('subdir')
    browser.change_dir(subdir)
    return jsonify({'current_path': browser.current_path})

@app.route('/ssh/download', methods=['POST'])
def download_file():
    browser = get_browser()
    if not browser:
        return jsonify({'error': 'Not connected'}), 401
    data = request.json
    filename = data.get('filename')
    local_path = browser.download_file(filename)
    if not local_path:
        return jsonify({'error': 'Download failed'}), 500
    return send_file(local_path, as_attachment=True)

@app.route('/ssh/disconnect', methods=['POST'])
def disconnect():
    browser = get_browser()
    if browser:
        browser.close()
        sid = session.get('sid')
        if sid:
            ssh_sessions.pop(sid, None)
        session.pop('sid', None)
    return jsonify({'message': 'Disconnected'})

@app.route('/ssh/tail', methods=['POST'])
def tail_log():
    browser = get_browser()
    if not browser:
        return jsonify({'error': 'Not connected'}), 401
    data = request.json
    filename = data.get('filename')
    if not filename:
        return jsonify({'error': 'No filename provided'}), 400
    
    def generate():
        transport = browser.ssh.get_transport()
        channel = transport.open_session()
        channel.exec_command(f"tail -F {filename}")
        try:
            while True:
                if channel.recv_ready():
                    chunk= channel.recv(4096)
                    if not chunk:
                        break
                    yield chunk.decode()
        except GeneratorExit:
            pass
        finally:
            channel.close()
    return Response(generate(), mimetype='text/plain')
    
if __name__ == '__main__':
    app.run(debug=True)
