import logging
import re
from collections import defaultdict
from typing import List, Optional, Dict
from pathlib import Path


def filter_log_lines(
    filepath: Path,
    keyword: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    levels: Optional[List[str]] = None,
) -> List[str]:
    if not filepath.exists():
        logging.error(f"File not found: {filepath}")
        return []

    try:
        lines = filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception as e:
        logging.error(f"Error reading file {filepath}: {e}")
        return []

    if levels:
        # Only keep lines that contain one of the selected log levels (word boundary match)
        level_pattern = re.compile(
            r"\b(" + "|".join(re.escape(lvl) for lvl in levels) + r")\b"
        )
        lines = [line for line in lines if level_pattern.search(line)]

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


def drill_down_by_program(
    filepath: Path,
    keyword: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    levels: Optional[List[str]] = None,
) -> Dict[str, List[str]]:
    lines = filter_log_lines(filepath, keyword, start_date, end_date, levels)
    if not lines:
        return {}
    program_pattern = re.compile(r"\s((?:isi_|celog|/boot)[\w./-]+)(?=\[|:)")
    grouped_logs = defaultdict(list)
    for line in lines:
        match = program_pattern.search(line)
        if match:
            prog_name = match.group(1)
            grouped_logs[prog_name].append(line.strip())
    return grouped_logs


def summarize_log(
    filepath: Path,
    keyword: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    levels: Optional[List[str]] = None,
) -> str:
    lines = filter_log_lines(filepath, keyword, start_date, end_date, levels)
    total_lines = len(lines)
    program_pattern = re.compile(r"\s((?:isi_|celog|/boot)[\w./-]+)(?=\[|:)")
    timestamp_pattern = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
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
    if levels:
        summary.append(f"🔔 Filtered by log level(s): {', '.join(levels)}")
    summary.append(f"🧠 Unique programs: {len(program_counts)}")
    if program_counts:
        top_programs = sorted(program_counts.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]
        summary.append("🏷️ Top 5 programs:")
        for prog, count in top_programs:
            summary.append(f"  • {prog}: {count} entries")
    if timestamps:
        summary.append(f"🕒 Time range: {min(timestamps)} → {max(timestamps)}")
    if start_date or end_date:
        summary.append(
            f"📅 Filtered by date range: {start_date or '...'} → {end_date or '...'}"
        )
    return "\n".join(summary)
