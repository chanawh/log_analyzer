import sys
import os
import werkzeug
import json
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, request, jsonify, send_file, Response, session
from pathlib import Path
from core.log_utils import filter_log_lines, summarize_log, drill_down_by_program
from core.llm_utils import explain_log_entry
from core.ssh_browser import SSHBrowser

app = Flask(__name__)
app.secret_key = "supersecret" # Set this securely in prod

UPLOAD_DIR = Path(os.path.dirname(__file__)) / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# --- SSH session management ---
ssh_sessions = {}

def get_browser():
    sid = session.get('sid')
    if sid and sid in ssh_sessions:
        return ssh_sessions[sid]
    return None

@app.route("/ssh/connect", methods=["POST"])
def connect_ssh():
    data = request.json
    host = data.get("host")
    username = data.get("username")
    password = data.get("password")
    if not host or not username or not password:
        return jsonify({"error": "Missing credentials"}), 400
    browser = SSHBrowser()
    try:
        browser.connect(host, username, password)
        sid = os.urandom(16).hex()
        ssh_sessions[sid] = browser
        session["sid"] = sid
        return jsonify({"message": "Connected", "current_path": browser.current_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/ssh/list", methods=["GET"])
def list_dir():
    browser = get_browser()
    if not browser:
        return jsonify({"error": "Not connected"}), 401
    path = request.args.get("path", browser.current_path)
    items = browser.list_dir(path)
    return jsonify({"items": [{"name": n, "is_dir": d} for n, d in items]})

@app.route("/ssh/change", methods=["POST"])
def change_dir():
    browser = get_browser()
    if not browser:
        return jsonify({"error": "Not connected"}), 401
    data = request.json
    subdir = data.get("subdir")
    browser.change_dir(subdir)
    return jsonify({"current_path": browser.current_path})

@app.route("/ssh/download", methods=["POST"])
def download_file():
    browser = get_browser()
    if not browser:
        return jsonify({"error": "Not connected"}), 401
    data = request.json
    filename = data.get("filename")
    local_path = browser.download_file(filename)
    if not local_path:
        return jsonify({"error": "Download failed"}), 500
    return send_file(local_path, as_attachment=True)

@app.route("/ssh/disconnect", methods=["POST"])
def disconnect():
    browser = get_browser()
    if browser:
        browser.close()
        sid = session.get("sid")
        if sid:
            ssh_sessions.pop(sid, None)
        session.pop("sid", None)
    return jsonify({"message": "Disconnected"})

# --- LIVE TAIL route ---
@app.route("/ssh/tail", methods=["POST"])
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
                    chunk = channel.recv(4096)
                    if chunk:
                        yield chunk.decode()
                elif channel.exit_status_ready():
                    break
                else:
                    time.sleep(0.2)
        except GeneratorExit:
            pass
        finally:
            channel.close()

    return Response(generate(), mimetype='text/plain')

# --- MAIN web routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    summary, lines, grouped, error = "", [], {}, None
    chart_counts = {}
    timestamps = []
    custom_categories = {}
    categories_input = ""
    selected_category = None
    category_names = []
    if request.method == "POST":
        file = request.files.get("logfile")
        keyword = request.form.get("keyword", "").strip()
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        categories_input = request.form.get("categories", "").strip()
        selected_category = request.form.get("selected_category", "").strip()
        filepath = None
        if file and file.filename:
            safe_filename = werkzeug.utils.secure_filename(file.filename)
            filepath = UPLOAD_DIR / f"uploaded_{safe_filename}"
            file.save(str(filepath))
        # Parse custom categories input
        if categories_input:
            for line in categories_input.splitlines():
                if ":" in line:
                    cat, pat = line.split(":", 1)
                    custom_categories[cat.strip()] = pat.strip()
            category_names = list(custom_categories.keys())
        try:
            if filepath and filepath.exists():
                lines = filter_log_lines(filepath, keyword, start_date, end_date, None) # levels removed
                import re
                ts_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})')
                timestamps = []
                if custom_categories:
                    grouped = {}
                    for cat, pat in custom_categories.items():
                        try:
                            matcher = re.compile(pat)
                            grouped[cat] = [line for line in lines if matcher.search(line)]
                        except re.error:
                            grouped[cat] = []
                    chart_counts = {cat: len(entries) for cat, entries in grouped.items()}
                    for entries in grouped.values():
                        for line in entries:
                            ts = ts_pattern.search(line)
                            if ts:
                                timestamps.append(ts.group(1))
                    total_lines = sum(chart_counts.values())
                    summary_lines = [f"📄 Total lines (after filtering): {total_lines}"]
                    if keyword:
                        summary_lines.append(f"🔍 Filtered by keyword: '{keyword}'")
                    summary_lines.append(f"🗂️ Custom categories: {len(grouped)}")
                    if grouped:
                        summary_lines.append("🏷️ Category counts:")
                        for cat, entries in grouped.items():
                            summary_lines.append(f"  • {cat}: {len(entries)} entries")
                    if timestamps:
                        summary_lines.append(f"🕒 Time range: {min(timestamps)} → {max(timestamps)}")
                    if start_date or end_date:
                        summary_lines.append(f"📅 Filtered by date range: {start_date or '...'} → {end_date or '...'}")
                    summary = "\n".join(summary_lines)
                    # Option 2: let user choose category, default to first if none chosen
                    if category_names:
                        if not selected_category or selected_category not in category_names:
                            selected_category = category_names[0]
                        lines = grouped.get(selected_category, [])[:100]
                else:
                    # Fallback: group by keyword only if set, otherwise by program
                    if keyword:
                        grouped = {"Keyword": lines}
                        chart_counts = {"Keyword": len(lines)}
                    else:
                        grouped = drill_down_by_program(filepath)
                        chart_counts = {prog: len(entries) for prog, entries in grouped.items()}
                    for line in lines:
                        ts = ts_pattern.search(line)
                        if ts:
                            timestamps.append(ts.group(1))
                    summary = f"📄 Total lines: {len(lines)}"
                    if keyword:
                        summary += f"\n🔍 Filtered by keyword: '{keyword}'\n"
                    summary += f"\n🏷️ Group counts:\n"
                    for key, cnt in chart_counts.items():
                        summary += f"  • {key}: {cnt} entries\n"
                    if timestamps:
                        summary += f"🕒 Time range: {min(timestamps)} → {max(timestamps)}"
                    if start_date or end_date:
                        summary += f"\n📅 Filtered by date range: {start_date or '...'} → {end_date or '...'}"
            else:
                error = "No log file uploaded."
        except Exception as e:
            error = str(e)
        finally:
            if filepath and filepath.exists():
                filepath.unlink()
    chart_data = {
        "program_counts": chart_counts,  # Used for both bar/pie
        "level_counts": chart_counts,    # Pie chart now matches categories/keywords
        "timestamps": timestamps,
    }
    return render_template(
        "index.html",
        summary=summary,
        lines=lines[:100],
        grouped=grouped,
        error=error,
        chart_data=json.dumps(chart_data),
        categories_input=categories_input,
        category_names=category_names,
        selected_category=selected_category
    )

@app.route("/explain", methods=["POST"])
def explain():
    log_text = request.form.get("log_text", "")
    explanation = ""
    if log_text:
        explanation = explain_log_entry(log_text)
    return render_template("explain.html", log_text=log_text, explanation=explanation)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")