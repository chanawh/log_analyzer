import sys
import os
import werkzeug
import json
import time
from uuid import uuid4
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.ssh_api import connect_ssh, list_dir, change_dir, download_file, disconnect, tail_log

from flask import Flask, render_template, request, jsonify, send_file, Response, session
from pathlib import Path
from core.log_utils import filter_log_lines, summarize_log, drill_down_by_program
from core.llm_utils import explain_log_entry
from core.ssh_browser import SSHBrowser

app = Flask(__name__)
app.secret_key = "supersecret" # Set this securely in prod

UPLOAD_DIR = Path(os.path.dirname(__file__)) / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ssh_sessions = {}

def get_browser():
    sid = session.get('sid')
    if sid and sid in ssh_sessions:
        return ssh_sessions[sid]
    return None

# --- Add sorting helper ---
import re
def get_date(line):
    m = re.search(r'(\d{4}-\d{2}-\d{2})', line)
    return m.group(1) if m else ""

@app.route("/", methods=["GET"])
def index():
    uploaded_path = session.get("uploaded_filepath")
    has_file = uploaded_path and Path(uploaded_path).exists()
    return render_template(
        "index.html",
        summary="",
        lines=[],
        grouped={},
        error=None,
        chart_data=json.dumps({}),
        categories_input="",
        category_names=[],
        selected_category=None,
        has_file=has_file
    )

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("logfile")
    if not file or not file.filename:
        return jsonify({"error": "No file uploaded."}), 400
    safe_filename = werkzeug.utils.secure_filename(file.filename)
    unique_name = f"{uuid4()}_{safe_filename}"
    filepath = UPLOAD_DIR / unique_name
    file.save(str(filepath))
    session["uploaded_filepath"] = str(filepath)
    return jsonify({"success": True})

@app.route("/analyze", methods=["POST"])
def analyze():
    uploaded_path = session.get("uploaded_filepath")
    if not uploaded_path or not Path(uploaded_path).exists():
        return jsonify({"error": "No log file uploaded."}), 400
    filepath = Path(uploaded_path)
    data = request.json or {}
    keyword = data.get("keyword", "").strip()
    start_date = data.get("start_date", "").strip()
    end_date = data.get("end_date", "").strip()
    categories_input = data.get("categories", "").strip()
    selected_category = data.get("selected_category", "").strip()
    custom_categories = {}
    category_names = []

    # Parse custom categories input
    if categories_input:
        for line in categories_input.splitlines():
            if ":" in line:
                cat, pat = line.split(":", 1)
                custom_categories[cat.strip()] = pat.strip()
        category_names = list(custom_categories.keys())

    try:
        lines = filter_log_lines(filepath, keyword, start_date, end_date, None)
        ts_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})')
        timestamps = []
        chart_counts = {}
        grouped = {}
        summary = ""

        # ----------- time_series aggregation and total line ----------
        time_series = {}
        total_series = {}

        def update_total(date_hist):
            for d, v in date_hist.items():
                total_series[d] = total_series.get(d, 0) + v

        if custom_categories:
            for cat, pat in custom_categories.items():
                try:
                    matcher = re.compile(pat)
                    cat_lines = [line for line in lines if matcher.search(line)]
                    grouped[cat] = cat_lines
                    # Aggregate dates for each category
                    date_hist = {}
                    for line in cat_lines:
                        ts = ts_pattern.search(line)
                        if ts:
                            d = ts.group(1)
                            date_hist[d] = date_hist.get(d, 0) + 1
                    time_series[cat] = date_hist
                    update_total(date_hist)
                except re.error:
                    grouped[cat] = []
                    time_series[cat] = {}
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
                # --- SORT lines before slicing ---
                lines_sorted = sorted(grouped.get(selected_category, []), key=get_date)
                lines = lines_sorted[:100]
        else:
            if keyword:
                grouped = {"Keyword": lines}
                chart_counts = {"Keyword": len(lines)}
                # Aggregate per day for keyword
                date_hist = {}
                for line in lines:
                    ts = ts_pattern.search(line)
                    if ts:
                        d = ts.group(1)
                        date_hist[d] = date_hist.get(d, 0) + 1
                        timestamps.append(d)
                time_series["Keyword"] = date_hist
                update_total(date_hist)
            else:
                grouped = drill_down_by_program(filepath)
                chart_counts = {prog: len(entries) for prog, entries in grouped.items()}
                # Aggregate per day for each program group
                for prog, prog_lines in grouped.items():
                    date_hist = {}
                    for line in prog_lines:
                        ts = ts_pattern.search(line)
                        if ts:
                            d = ts.group(1)
                            date_hist[d] = date_hist.get(d, 0) + 1
                            timestamps.append(d)
                    time_series[prog] = date_hist
                    update_total(date_hist)
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
            # --- SORT lines before slicing ---
            lines_sorted = sorted(lines, key=get_date)
            lines = lines_sorted[:100]

        # Add total series as "Total"
        if total_series:
            time_series["Total"] = total_series

        chart_data = {
            "program_counts": chart_counts,
            "level_counts": chart_counts,
            "timestamps": timestamps,
            "time_series": time_series,
        }
        response = {
            "summary": summary,
            "lines": lines,
            "grouped": {k: v[:5] for k, v in grouped.items()},
            "chart_data": chart_data,
            "categories_input": categories_input,
            "category_names": category_names,
            "selected_category": selected_category,
            "error": None
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/clear_file", methods=["POST"])
def clear_file():
    uploaded_path = session.get("uploaded_filepath")
    if uploaded_path and Path(uploaded_path).exists():
        Path(uploaded_path).unlink(missing_ok=True)
    session.pop("uploaded_filepath", None)
    return jsonify({"success": True})

@app.route("/explain", methods=["POST"])
def explain():
    log_text = request.form.get("log_text", "")
    explanation = ""
    if log_text:
        explanation = explain_log_entry(log_text)
    return render_template("explain.html", log_text=log_text, explanation=explanation)

# --- SSH routes unchanged ---
@app.route("/ssh/connect", methods=["POST"])
def connect_ssh_route():
    return connect_ssh()

@app.route("/ssh/list", methods=["GET"])
def list_dir_route():
    return list_dir()

@app.route("/ssh/change", methods=["POST"])
def change_dir_route():
    return change_dir()

@app.route("/ssh/download", methods=["POST"])
def download_file_route():
    return download_file()

@app.route("/ssh/disconnect", methods=["POST"])
def disconnect_route():
    return disconnect()

@app.route("/ssh/tail", methods=["POST"])
def tail_log_route():
    return tail_log()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")