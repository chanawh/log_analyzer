import sys
import os
import werkzeug
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, request
from pathlib import Path
from core.log_utils import filter_log_lines, summarize_log, drill_down_by_program
from core.llm_utils import explain_log_entry  # <-- NEW: import your LLM utility

app = Flask(__name__)
app.secret_key = "change_this_to_a_random_secret"

UPLOAD_DIR = Path(os.path.dirname(__file__)) / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    summary, lines, grouped, error = "", [], {}, None
    program_counts = {}
    level_counts = {}
    timestamps = []
    if request.method == "POST":
        file = request.files.get("logfile")
        keyword = request.form.get("keyword", "").strip()
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        levels = request.form.getlist("levels")  # <-- get selected log levels
        filepath = None
        if file and file.filename:
            safe_filename = werkzeug.utils.secure_filename(file.filename)
            filepath = UPLOAD_DIR / f"uploaded_{safe_filename}"
            file.save(str(filepath))
        try:
            if filepath and filepath.exists():
                summary = summarize_log(filepath, keyword, start_date, end_date, levels)  # <-- Pass levels
                lines = filter_log_lines(filepath, keyword, start_date, end_date, levels) # <-- Pass levels
                grouped = drill_down_by_program(filepath)

                # Chart data extraction
                import re
                prog_pattern = re.compile(r'\s((?:isi_|celog|/boot)[\w./-]+)(?=\[|:)')
                level_pattern = re.compile(r'\b(INFO|ERROR|WARN|DEBUG)\b')
                ts_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})')
                program_counts = {}
                level_counts = {}
                timestamps = []
                for line in lines:
                    prog = prog_pattern.search(line)
                    lvl = level_pattern.search(line)
                    ts = ts_pattern.search(line)
                    if prog:
                        program_counts[prog.group(1)] = program_counts.get(prog.group(1), 0) + 1
                    if lvl:
                        level_counts[lvl.group(1)] = level_counts.get(lvl.group(1), 0) + 1
                    if ts:
                        timestamps.append(ts.group(1))
            else:
                error = "No log file uploaded."
        except Exception as e:
            error = str(e)
        finally:
            if filepath and filepath.exists():
                filepath.unlink()
    # Pass chart data as JSON
    chart_data = {
        "program_counts": program_counts,
        "level_counts": level_counts,
        "timestamps": timestamps,
    }
    return render_template(
        "index.html",
        summary=summary,
        lines=lines[:100],
        grouped=grouped,
        error=error,
        chart_data=json.dumps(chart_data)
    )

# NEW: Add route for LLM log explanation
@app.route("/explain", methods=["POST"])
def explain():
    log_text = request.form.get("log_text", "")
    explanation = ""
    if log_text:
        explanation = explain_log_entry(log_text)
    return render_template("explain.html", log_text=log_text, explanation=explanation)

if __name__ == "__main__":
    app.run(debug=True)