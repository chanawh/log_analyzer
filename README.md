# Log Analyzer

> **Modern, AI-powered log analysis for sysadmins, SREs, and developers.**  
> Upload, filter, and understand logs—locally or remotely—with charts, SSH browsing, and natural language explanations.

---

## 🔍 About Log Analyzer

Log Analyzer is a full-featured tool for rapid investigation and understanding of complex log files. Designed for sysadmins, SREs, and anyone who works with infrastructure or application logs, it offers a web UI and desktop GUI, remote SSH log browser, rich filters, and local LLM-powered explanations to make troubleshooting and root cause analysis faster than ever.

**Key Features:**

- Upload or browse logs locally and via SSH on remote servers
- Advanced filtering (keyword/regex, date, category)
- Summarize and visualize logs with interactive charts
- Instantly explain log lines using a local LLM (Phi-2 or Mistral 7B)
- Easy to run via Docker or Python

---

## 🚀 Get Started in 1 Minute

### Docker (Recommended)

```bash
docker-compose up --build
# Visit http://localhost:5000
```

### Local Python

```bash
pip install -r requirements.txt
python api/webui.py      # Launch web UI
python main.py           # Launch desktop GUI
```

---

## 🖥️ Screenshots

### Web UI

![Web UI Screenshot](docs/screenshot_webui.png)

### Desktop GUI

![GUI Screenshot](docs/screenshot_gui.png)

---

## 📝 Quick Start

- **Upload Log**: In the web UI or GUI, select a log file to analyze.
- **Filter & Analyze**: Use keyword (regex), date, or custom categories to filter.
- **SSH**: Connect to remote servers, browse directories, and download logs securely.
- **Explain**: Select any log line for an LLM-powered, plain English explanation.
- **Visualize**: See log patterns and timelines with interactive charts.

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
