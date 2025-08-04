import logging
import os
import re
import stat
import paramiko
from collections import defaultdict
from typing import List, Optional, Dict
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import posixpath

# 📋 Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("log_analysis.log"),
        logging.StreamHandler()
    ]
)

def filter_log_lines(filepath: Path, keyword: Optional[str] = None,
                     start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[str]:
    if not filepath.exists():
        logging.error(f"File not found: {filepath}")
        return []

    try:
        lines = filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception as e:
        logging.error(f"Error reading file {filepath}: {e}")
        return []

    if keyword:
        try:
            pattern = re.compile(keyword)
            lines = [line for line in lines if pattern.search(line)]
        except re.error as e:
            logging.error(f"Invalid regex pattern: {e}")
            return []

    if start_date or end_date:
        date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")

        filtered_by_date = []
        for line in lines:
            match = date_pattern.search(line)
            if match:
                line_date = match.group(1)
                if start_date and line_date < start_date:
                    continue
                if end_date and line_date > end_date:
                    continue
                filtered_by_date.append(line)
        lines = filtered_by_date

    return lines


def drill_down_by_program(filepath: Path) -> Dict[str, List[str]]:
    lines = filter_log_lines(filepath)
    if not lines:
        return {}
    program_pattern = re.compile(r'\s((?:isi_|celog|/boot)[\w./-]+)(?=\[|:)')
    grouped_logs = defaultdict(list)
    for line in lines:
        match = program_pattern.search(line)
        if match:
            prog_name = match.group(1)
            grouped_logs[prog_name].append(line.strip())
    return grouped_logs


def summarize_log(filepath: Path, keyword: Optional[str] = None,
                start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    lines = filter_log_lines(filepath, keyword)
    total_lines = len(lines)
    program_pattern = re.compile(r'\s((?:isi_|celog|/boot)[\w./-]+)(?=\[|:)')
    timestamp_pattern = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
    program_counts = defaultdict(int)
    timestamps = []
    for line in lines:
        match = program_pattern.search(line)
        if match:
            program_counts[match.group(1)] += 1
        ts_match = timestamp_pattern.search(line)
        if ts_match:
            timestamps.append(ts_match.group(0))
    summary = [f"📄 Total lines: {total_lines}"]
    if keyword:
        summary.append(f"🔍 Lines containing '{keyword}': {total_lines}")
    summary.append(f"🧠 Unique programs: {len(program_counts)}")
    if program_counts:
        top_programs = sorted(program_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        summary.append("🏷️ Top 5 programs:")
        for prog, count in top_programs:
            summary.append(f"  • {prog}: {count} entries")
    if timestamps:
        summary.append(f"🕒 Time range: {min(timestamps)} → {max(timestamps)}")
    
    
    if start_date or end_date:
        summary.append(f"📅 Filtered by date range: {start_date or '...'} → {end_date or '...'}")

    return "\n".join(summary)

class SSHBrowser:
    def __init__(self):
        self.ssh = None
        self.sftp = None
        self.current_path = "/"

    def connect(self, host, username, password):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(host, username=username, password=password)
        self.sftp = self.ssh.open_sftp()
        self.current_path = self.sftp.normalize(".")

    def list_dir(self, path):
        try:
            items = self.sftp.listdir_attr(path)
            return [(item.filename, stat.S_ISDIR(item.st_mode)) for item in items]
        except Exception as e:
            logging.error(f"Failed to list directory: {e}")
            return []

    def change_dir(self, subdir):
        if subdir == "..":
            self.current_path = os.path.dirname(self.current_path.rstrip("/"))
        else:
            self.current_path = os.path.join(self.current_path, subdir)
        return self.list_dir(self.current_path)

    def download_file(self, filename):
        remote_path = posixpath.join(self.current_path, filename)
        local_path = os.path.join(os.getcwd(), filename)

        try:
            # Check if file exists remotely
            remote_files = self.sftp.listdir(self.current_path)
            if filename not in remote_files:
                logging.error(f"File '{filename}' not found in remote directory '{self.current_path}'")
                return ""

            # Attempt to download
            self.sftp.get(remote_path, local_path)
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                logging.info(f"Downloaded file to {local_path} ({os.path.getsize(local_path)} bytes)")
            else:
                logging.warning(f"Downloaded file is empty or missing: {local_path}")
            return local_path

        except FileNotFoundError:
            logging.error(f"Remote file not found: {remote_path}")
            return ""
        except Exception as e:
            logging.error(f"Failed to download file: {e}")
            return ""

    def close(self):
        if self.sftp: self.sftp.close()
        if self.ssh: self.ssh.close()

def launch_gui():
    browser = SSHBrowser()

    def browse_file():
        path = filedialog.askopenfilename(filetypes=[("Log files", "*.log *.txt"), ("All files", "*.*")])
        if path:
            file_entry.delete(0, tk.END)
            file_entry.insert(0, path)


    def run_analysis():
        start_date = start_date_entry.get().strip()
        end_date = end_date_entry.get().strip()
        filepath = Path(file_entry.get())
        keyword = keyword_entry.get().strip()
        
        lines = filter_log_lines(filepath, keyword, start_date, end_date)

        if not filepath.exists():
            messagebox.showerror("Error", "File not found.")
            return
        if filepath.is_dir():
            messagebox.showerror("Error", "Selected path is a directory, not a file.")
            return
        output_text.delete(1.0, tk.END)
        try:
            summary = summarize_log(filepath, keyword)
        except re.error as e:
            messagebox.showerror("Regex Error", f"Invalid regex pattern: {e}")
            return

        output_text.insert(tk.END, "📊 Log Summary:\n" + summary + "\n\n")
        if keyword:
            try:
                lines = filter_log_lines(filepath, keyword)
            except re.error as e:
                messagebox.showerror("Regex Error", f"Invalid regex pattern: {e}")
                return
            output_text.insert(tk.END, "📌 Matching Lines:\n")
            output_text.insert(tk.END, "\n".join(lines[:100]) + ("\n... (truncated)" if len(lines) > 100 else ""))
        else:
            grouped = drill_down_by_program(filepath)
            if not grouped:
                output_text.insert(tk.END, "No matching programs found.")
                return
            output_text.insert(tk.END, "📁 Grouped by Program:\n")
            for prog, entries in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
                output_text.insert(tk.END, f"{prog}: {len(entries)} entries\n")
                for entry in entries[:5]:
                    output_text.insert(tk.END, f" • {entry}\n")
                if len(entries) > 5:
                    output_text.insert(tk.END, f" ...and {len(entries) - 5} more\n")
            output_text.insert(tk.END, "\n")


        output_text.delete(1.0, tk.END)
        summary = summarize_log(filepath, keyword, start_date, end_date)
        output_text.insert(tk.END, "📊 Log Summary:\n" + summary + "\n\n")
        if keyword:
            lines = filter_log_lines(filepath, keyword, start_date, end_date)
            output_text.insert(tk.END, "📌 Matching Lines:\n")
            output_text.insert(tk.END, "\n".join(lines[:100]) + ("\n... (truncated)" if len(lines) > 100 else ""))
        else:
            grouped = drill_down_by_program(filepath)
            if not grouped:
                output_text.insert(tk.END, "No matching programs found.")
                return
            output_text.insert(tk.END, "📁 Grouped by Program:\n")
            for prog, entries in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
                output_text.insert(tk.END, f"{prog}: {len(entries)} entries\n")
                for entry in entries[:5]:
                    output_text.insert(tk.END, f"  • {entry}\n")
                if len(entries) > 5:
                    output_text.insert(tk.END, f"  ...and {len(entries) - 5} more\n")
                output_text.insert(tk.END, "\n")

    def connect_ssh():
        try:
            browser.connect(host_entry.get(), user_entry.get(), pass_entry.get())
            update_remote_list()
        except Exception as e:
            messagebox.showerror("SSH Error", str(e))

    def update_remote_list():
        remote_path_var.set(browser.current_path)
        file_list.delete(0, tk.END)
        for name, is_dir in browser.list_dir(browser.current_path):
            prefix = "[DIR] " if is_dir else "      "
            file_list.insert(tk.END, prefix + name)

    def go_up():
        browser.change_dir("..")
        update_remote_list()

    def enter_dir():
        selection = file_list.curselection()
        if not selection:
            return
        name = file_list.get(selection[0]).strip()
        if name.startswith("[DIR]"):
            dirname = name[6:].strip()
            browser.change_dir(dirname)
            update_remote_list()

    def download_selected():
        selection = file_list.curselection()
        if not selection:
            return

        name = file_list.get(selection[0])
        if name.startswith("[DIR]"):
            messagebox.showinfo("Info", "Please select a file, not a directory.")
            return

        filename = name.replace("[DIR]", "").strip()
        if not filename:
            messagebox.showerror("Error", "No file selected.")
            return

        local_path = browser.download_file(filename)
        if not local_path or Path(local_path).is_dir():
            messagebox.showerror("Error", "Download failed or selected item is a directory.")
            return

        file_entry.delete(0, tk.END)
        file_entry.insert(0, local_path)
        run_analysis()

    root = tk.Tk()
    root.title("Log Analyzer with SSH")

    tk.Label(root, text="Log File:").grid(row=0, column=0, sticky="e")
    file_entry = tk.Entry(root, width=50)
    file_entry.grid(row=0, column=1)
    tk.Button(root, text="Browse", command=browse_file).grid(row=0, column=2)

    tk.Label(root, text="Keyword (regex supported):").grid(row=1, column=0, sticky="e")
    keyword_entry = tk.Entry(root, width=50)
    keyword_entry.grid(row=1, column=1, columnspan=2)

    tk.Button(root, text="Analyze", command=run_analysis).grid(row=2, column=1, pady=10)

    tk.Label(root, text="SSH Host:").grid(row=3, column=0, sticky="e")
    host_entry = tk.Entry(root, width=50)
    host_entry.grid(row=3, column=1, columnspan=2)

    tk.Label(root, text="Username:").grid(row=4, column=0, sticky="e")
    user_entry = tk.Entry(root, width=50)
    user_entry.grid(row=4, column=1, columnspan=2)

    tk.Label(root, text="Password:").grid(row=5, column=0, sticky="e")
    pass_entry = tk.Entry(root, width=50, show="*")
    pass_entry.grid(row=5, column=1, columnspan=2)

    tk.Button(root, text="Connect SSH", command=connect_ssh).grid(row=6, column=1, pady=5)

    remote_path_var = tk.StringVar()
    tk.Label(root, textvariable=remote_path_var).grid(row=7, column=0, columnspan=3)

    file_list = tk.Listbox(root, width=80, height=10)
    file_list.grid(row=8, column=0, columnspan=3, padx=10)

    tk.Button(root, text="Go Up", command=go_up).grid(row=9, column=0)
    tk.Button(root, text="Enter Directory", command=enter_dir).grid(row=9, column=1)
    tk.Button(root, text="Download & Analyze", command=download_selected).grid(row=9, column=2)

    output_text = scrolledtext.ScrolledText(root, width=100, height=20)
    output_text.grid(row=10, column=0, columnspan=3, padx=10, pady=10)


    tk.Label(root, text="Enter Directory Path:").grid(row=11, column=0, sticky="e")
    manual_dir_entry = tk.Entry(root, width=50)
    manual_dir_entry.grid(row=11, column=1)
    tk.Button(root, text="Go to Directory", command=lambda: go_to_manual_dir()).grid(row=11, column=2)

    
    tk.Label(root, text="Start Date (YYYY-MM-DD):").grid(row=12, column=0, sticky="e")
    start_date_entry = tk.Entry(root, width=50)
    start_date_entry.grid(row=12, column=1, columnspan=2)

    tk.Label(root, text="End Date (YYYY-MM-DD):").grid(row=13, column=0, sticky="e")
    end_date_entry = tk.Entry(root, width=50)
    end_date_entry.grid(row=13, column=1, columnspan=2)


    def go_to_manual_dir():
        path = manual_dir_entry.get().strip()
        if path:

            try:
                # Normalize and validate the path
                browser.current_path = browser.sftp.normalize(path)
                update_remote_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to enter directory: {e}")
    root.mainloop()

if __name__ == "__main__":
    launch_gui()
