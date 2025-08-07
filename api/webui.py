import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, request, redirect, url_for, flash
from pathlib import Path
from core.log_utils import filter_log_lines, summarize_log, drill_down_by_program

app = Flask(__name__)
app.secret_key = "change_this_to_a_random_secret"

@app.route("/", methods=["GET", "POST"])
def index():
    summary, lines, grouped, error = "", [], {}, None

    if request.method == "POST":
        file = request.files.get("logfile")
        keyword = request.form.get("keyword", "").strip()
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        filepath = None
        if file:
            filepath = Path("uploaded_" + file.filename)
            file.save(str(filepath))
        try:
            if filepath and filepath.exists():
                summary = summarize_log(filepath, keyword, start_date, end_date)
                lines = filter_log_lines(filepath, keyword, start_date, end_date)
                grouped = drill_down_by_program(filepath)
            else:
                error = "No log file uploaded."
        except Exception as e:
            error = str(e)
        finally:
            if filepath and filepath.exists():
                filepath.unlink()
    return render_template("index.html", summary=summary, lines=lines[:100], grouped=grouped, error=error)

if __name__ == "__main__":
    app.run(debug=True)