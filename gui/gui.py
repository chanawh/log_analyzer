from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from core.log_utils import filter_log_lines, summarize_log, drill_down_by_program
from core.ssh_browser import SSHBrowser

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
            summary = summarize_log(filepath, keyword, start_date, end_date)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to summarize log: {e}")
            return

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
                browser.current_path = browser.sftp.normalize(path)
                update_remote_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to enter directory: {e}")

    root.mainloop()