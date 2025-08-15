# Log Analyzer

A full-featured log analysis tool with both a web UI and a desktop GUI, designed for rapid investigation of large log files. Features advanced filtering, custom categories, SSH remote access, and LLM-powered log explanations.

---

## 🚀 Features

- **Web UI**: Upload and analyze logs in your browser—filter by keyword (regex supported), date range, and custom categories.
- **Desktop GUI**: Launch a Tkinter-based GUI for offline log analysis.
- **SSH Browser**: Connect to remote servers, browse directories, and download logs via SSH directly from the web or GUI.
- **LLM Explanations**: Get natural language explanations of log entries using a local LLM (e.g. Microsoft Phi-2 or Mistral 7B).
- **Charts & Summaries**: Visualize log statistics, activity over time, and category distributions.
- **Dockerized**: Runs easily anywhere via Docker or Docker Compose.
- **CI/CD**: Automated linting, testing, and Docker builds via GitHub Actions.

---

## 🖥️ Screenshots

### Web UI

![Web UI Screenshot](docs/screenshot_webui.png)

### Desktop GUI

![GUI Screenshot](docs/screenshot_gui.png)

---

## 📝 Quick Start

### 1. Docker (Recommended)

```bash
docker-compose up --build
# Visit http://localhost:5000
```

### 2. Local Python

```bash
pip install -r requirements.txt
python api/webui.py      # Launch web UI
python main.py           # Launch desktop GUI
```

---

## 💡 Usage Highlights

- **Upload Log File**: Use the web UI or GUI to select and upload a log file.
- **Filter & Analyze**: Filter by keyword (regex), date range, and group by log program or custom categories.
- **SSH Remote Access**: Enter SSH credentials, browse directories, and download logs for analysis.
- **Explain Log Entries**: Select any log line and get an LLM-based, plain English explanation.
- **Charts**: Interactive charts display log activity, categories, and trends.

---

## 🛠️ Tech Stack

- **Backend**: Python (Flask)
- **Frontend**: HTML5, Bootstrap, Chart.js, Tkinter (for GUI)
- **SSH**: Paramiko
- **LLM**: HuggingFace Transformers (Phi-2/Mistral 7B, local inference)
- **Containerization**: Docker, Docker Compose
- **CI/CD**: GitHub Actions

---

## 🧪 Running Tests

```bash
pytest tests/
```

---

## 🤝 Contributing

Contributions are welcome! Please open issues or submit pull requests for new features, bugfixes, or improvements.

---

## 📄 License

[MIT License](LICENSE)

---

## 👤 Author

- [chanawh](https://github.com/chanawh)

---

## 🌐 Demo

Optionally, add a link to a live deployment or video demo if available.
