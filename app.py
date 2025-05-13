import os
import json
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta, date
from collections import defaultdict
import re

app = Flask(__name__)

# --- Configuration ---
LOG_FILE_PATH = os.path.join("logs", "data_activity.json")
# For browsers, we'll list them by process name in the process list,
# and window titles will show the full title.
BROWSER_PROCESSES = ["firefox.exe", "chrome.exe", "msedge.exe", "safari.exe"] # Add more if needed

# --- Helper Functions ---
def format_ms_to_readable(ms):
    """Converts milliseconds to a human-readable string (e.g., 1h 15m 30s)."""
    if ms is None or ms < 0:
        return "0s"
    
    s = round(ms / 1000)
    if s == 0 and ms > 0: # for very short durations like 500ms
        return f"{ms}ms"
    if s == 0:
        return "0s"

    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    parts = []
    if d > 0:
        parts.append(f"{d}d")
    if h > 0:
        parts.append(f"{h}h")
    if m > 0:
        parts.append(f"{m}m")
    if s > 0 or not parts: # Always show seconds if other parts are zero, or if it's the only unit
        parts.append(f"{s}s")
    
    return " ".join(parts)

def parse_log_timestamp(line_timestamp_str):
    """Parses the timestamp at the beginning of a log line."""
    try:
        # Example: 2025-05-06 00:05:33,873
        return datetime.strptime(line_timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
    except ValueError:
        # Try without milliseconds if that fails
        try:
            return datetime.strptime(line_timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            app.logger.warning(f"Could not parse log line timestamp: {line_timestamp_str}")
            return None

def get_stats_for_date_range(start_date_obj, end_date_obj):
    """
    Processes logs for a given date range and aggregates statistics.
    Returns a dictionary with aggregated stats.
    """
    # Initialize aggregators for the entire period
    period_window_durations = defaultdict(lambda: {"total_duration_ms": 0, "process_names": set()})
    period_process_durations = defaultdict(int)
    period_distractions = []
    period_total_time_ms = 0

    # Iterate through each day in the range
    current_date = start_date_obj
    while current_date <= end_date_obj:
        daily_stats = get_daily_stats(current_date)
        
        period_total_time_ms += daily_stats.get("total_time_ms", 0)

        # Aggregate window durations
        if daily_stats.get("raw_window_durations"):
            for title, data in daily_stats["raw_window_durations"].items():
                duration_ms = data.get("total", 0)
                period_window_durations[title]["total_duration_ms"] += duration_ms
                process_name = daily_stats.get("raw_window_to_process_map", {}).get(title, "Unknown Process")
                period_window_durations[title]["process_names"].add(process_name)
        
        # Aggregate distractions
        period_distractions.extend(daily_stats.get("distractions_list", []))
        
        current_date += timedelta(days=1)

    # Post-process aggregated window data to determine primary process name and sort
    processed_period_windows = []
    for title, data in period_window_durations.items():
        # Choose one process name, e.g., the first one alphabetically or just join them
        process_name_display = " / ".join(sorted(list(data["process_names"]))) if data["process_names"] else "Unknown Process"
        processed_period_windows.append({
            "title": title,
            "duration_ms": data["total_duration_ms"],
            "duration_formatted": format_ms_to_readable(data["total_duration_ms"]),
            "process_name": process_name_display
        })
    
    # Sort windows by duration
    processed_period_windows.sort(key=lambda x: x["duration_ms"], reverse=True)

    # Aggregate process durations from the detailed window data
    for window_data in processed_period_windows:
        # For simplicity, if multiple processes are listed, attribute to the first one for process summary
        # A more accurate way would be to get process directly from window_info if available
        # However, window_durations is keyed by title.
        # Let's rebuild process_durations from aggregated_window_durations
        # This part is a bit tricky if a window title maps to multiple processes over time.
        # We'll use the process names associated during aggregation.
        first_process_in_set = next(iter(period_window_durations[window_data["title"]]["process_names"]), "Unknown Process")
        if first_process_in_set != "Unknown Process": # Avoid double counting if split
             period_process_durations[first_process_in_set] += window_data["duration_ms"]


    # Sort processes by duration
    sorted_period_processes = sorted(period_process_durations.items(), key=lambda item: item[1], reverse=True)
    top_processes_formatted = [{
        "process_name": p_name,
        "duration_ms": dur_ms,
        "duration_formatted": format_ms_to_readable(dur_ms)
    } for p_name, dur_ms in sorted_period_processes]


    return {
        "start_date": start_date_obj.strftime("%Y-%m-%d"),
        "end_date": end_date_obj.strftime("%Y-%m-%d"),
        "total_time_over_period_ms": period_total_time_ms,
        "total_time_over_period_formatted": format_ms_to_readable(period_total_time_ms),
        "top_windows_over_period": processed_period_windows[:10], # Top 10 for API
        "top_processes_over_period": top_processes_formatted[:10], # Top 10 for API
        "distractions_over_period": sorted(period_distractions, key=lambda x: x.get("timestamp_iso", ""), reverse=True)
    }


def get_daily_stats(target_date_obj):
    """
    Parses the log file for a specific date and extracts statistics.
    target_date_obj: a datetime.date object.
    """
    latest_daily_window_durations = None
    daily_window_to_process_map = {}
    daily_distractions = []
    last_window_info_for_linking = None # To link ai_analysis to its window_info

    try:
        with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # Extract timestamp from the beginning of the line
                # Format: YYYY-MM-DD HH:MM:SS,ms - 
                match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d{3})?)", line)
                if not match:
                    continue
                
                log_line_timestamp_str = match.group(1)
                log_datetime = parse_log_timestamp(log_line_timestamp_str)

                if not log_datetime or log_datetime.date() != target_date_obj:
                    continue

                # Process different types of log entries
                try:
                    if "window_info:" in line:
                        json_str = line.split("window_info:", 1)[1].strip()
                        info = json.loads(json_str)
                        daily_window_to_process_map[info["window_title"]] = info["process_name"]
                        last_window_info_for_linking = {
                            "title": info["window_title"],
                            "process": info["process_name"],
                            "timestamp_iso": info["timestamp"], # ISO format from JSON
                            "timestamp_display": datetime.fromisoformat(info["timestamp"]).strftime("%H:%M:%S")
                        }
                    elif "ai_analysis:" in line:
                        json_str = line.split("ai_analysis:", 1)[1].strip()
                        analysis_data = json.loads(json_str)
                        if analysis_data.get("analysis", {}).get("is_distracted") and last_window_info_for_linking:
                            daily_distractions.append({
                                **last_window_info_for_linking,
                                "reason": analysis_data.get("analysis", {}).get("reason", "No reason provided")
                            })
                    elif "window_durations:" in line:
                        json_str = line.split("window_durations:", 1)[1].strip()
                        # This will overwrite, keeping only the latest for the day
                        latest_daily_window_durations = json.loads(json_str) 
                except json.JSONDecodeError as e:
                    app.logger.error(f"JSON parsing error in line: {line}. Error: {e}")
                except Exception as e:
                    app.logger.error(f"Generic error processing line: {line}. Error: {e}")


    except FileNotFoundError:
        app.logger.error(f"Log file not found: {LOG_FILE_PATH}")
        return {"error": "Log file not found."} # Return error state
    except Exception as e:
        app.logger.error(f"Could not read log file: {e}")
        return {"error": f"Could not read log file: {e}"}

    # --- Post-processing for the day ---
    if latest_daily_window_durations is None:
        # No window_durations data for this day
        return {
            "date": target_date_obj.strftime("%Y-%m-%d"),
            "total_time_ms": 0,
            "total_time_formatted": format_ms_to_readable(0),
            "top_windows": [],
            "top_processes": [],
            "distractions_list": sorted(daily_distractions, key=lambda x: x.get("timestamp_iso",""), reverse=True),
            "raw_window_durations": {}, # Empty if none found
            "raw_window_to_process_map": daily_window_to_process_map, # Might have data even if durations don't
            "message": "No window duration data found for this day."
        }

    total_time_ms_today = sum(data.get("total", 0) for data in latest_daily_window_durations.values())

    # Prepare top windows list
    window_summary_list = []
    for title, data in latest_daily_window_durations.items():
        duration_ms = data.get("total", 0)
        process_name = daily_window_to_process_map.get(title, "Unknown Process")
        window_summary_list.append({
            "title": title,
            "duration_ms": duration_ms,
            "duration_formatted": format_ms_to_readable(duration_ms),
            "process_name": process_name
        })
    window_summary_list.sort(key=lambda x: x["duration_ms"], reverse=True)

    # Prepare top processes list
    process_time_aggregation = defaultdict(int)
    for title, data in latest_daily_window_durations.items():
        duration_ms = data.get("total", 0)
        process_name = daily_window_to_process_map.get(title, "Unknown Process")
        if process_name != "Unknown Process":
             process_time_aggregation[process_name] += duration_ms
    
    process_summary_list = [{
        "process_name": p_name,
        "duration_ms": dur_ms,
        "duration_formatted": format_ms_to_readable(dur_ms)
    } for p_name, dur_ms in sorted(process_time_aggregation.items(), key=lambda item: item[1], reverse=True)]

    return {
        "date": target_date_obj.strftime("%Y-%m-%d"),
        "total_time_ms": total_time_ms_today,
        "total_time_formatted": format_ms_to_readable(total_time_ms_today),
        "top_windows": window_summary_list[:10], # Top 10
        "top_processes": process_summary_list[:10], # Top 10
        "distractions_list": sorted(daily_distractions, key=lambda x: x.get("timestamp_iso",""), reverse=True),
        "raw_window_durations": latest_daily_window_durations,
        "raw_window_to_process_map": daily_window_to_process_map
    }

# --- Flask Routes ---
@app.route('/')
def index():
    """Main page displaying today's statistics."""
    today_obj = date.today()
    # For testing with provided sample data date:
    # today_obj = date(2025, 5, 6) 
    
    stats = get_daily_stats(today_obj)
    if "error" in stats:
        return render_template('index.html', error_message=stats["error"], today_date=today_obj.strftime("%Y-%m-%d"))
    
    return render_template('index.html', **stats, today_date=today_obj.strftime("%A, %B %d, %Y"))

@app.route('/api/activity_data', methods=['GET'])
def api_activity_data():
    """API endpoint to retrieve aggregated results over X days from current date."""
    try:
        days_str = request.args.get('days', '30')
        num_days = int(days_str)
        if num_days <= 0:
            return jsonify({"error": "Number of days must be positive."}), 400
    except ValueError:
        return jsonify({"error": "Invalid 'days' parameter. Must be an integer."}), 400

    end_date_obj = date.today()
    # For testing with provided sample data date:
    # end_date_obj = date(2025, 5, 6) 
    start_date_obj = end_date_obj - timedelta(days=num_days - 1)

    aggregated_stats = get_stats_for_date_range(start_date_obj, end_date_obj)
    
    if "error" in aggregated_stats: # Should not happen if get_daily_stats handles errors
        return jsonify(aggregated_stats), 500 
        
    return jsonify(aggregated_stats)


if __name__ == '__main__':
    # Create dummy logs directory and file if they don't exist for easy startup
    if not os.path.exists("logs"):
        os.makedirs("logs")
    if not os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, 'w', encoding='utf-8') as f:
            # Sample data for today (assuming today is 2025-05-06 for this example)
            # To make this work for the actual current day, these timestamps would need to be dynamic
            # or the user must have current logs.
            # For now, using the example date.
            today_str = date.today().strftime("%Y-%m-%d") # Actual today
            yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

            # Using fixed dates from example for consistency if user runs this script later
            fixed_today_example_date = "2025-05-06"
            fixed_yesterday_example_date = "2025-05-05"

            f.write(f"{fixed_today_example_date} 00:05:33,873 - window_info: {json.dumps({'window_title': 'Gemini — Mozilla Firefox', 'process_name': 'firefox.exe', 'active_time': 637, 'pid': 20908, 'timestamp': f'{fixed_today_example_date}T00:05:33.530234'})}\n")
            f.write(f"{fixed_today_example_date} 00:05:35,547 - ai_analysis: {json.dumps({'analysis': {'is_distracted': False, 'reason': 'Using Firefox.'}, 'token_usage': {}, 'analysis_type': 'window_title'})}\n")
            f.write(f"{fixed_today_example_date} 00:13:53,585 - window_info: {json.dumps({'window_title': 'app.py', 'process_name': 'Code.exe', 'active_time': 26, 'pid': 932, 'timestamp': f'{fixed_today_example_date}T00:13:53.257547'})}\n")
            f.write(f"{fixed_today_example_date} 00:13:54,907 - ai_analysis: {json.dumps({'analysis': {'is_distracted': False, 'reason': 'Coding.'}, 'token_usage': {}, 'analysis_type': 'window_title'})}\n")
            f.write(f"{fixed_today_example_date} 00:20:34,343 - window_durations: {json.dumps({'Gemini — Mozilla Firefox': {'total': 13740, 'consecutive': 3680}, 'app.py': {'total': 20000, 'consecutive': 1000}, 'YouTube — Mozilla Firefox': {'total': 5000, 'consecutive': 5000}})}\n")
            f.write(f"{fixed_today_example_date} 00:53:45,523 - window_info: {json.dumps({'window_title': 'YouTube — Mozilla Firefox', 'process_name': 'firefox.exe', 'active_time': 200, 'pid': 20908, 'timestamp': f'{fixed_today_example_date}T00:53:45.176305'})}\n")
            f.write(f"{fixed_today_example_date} 00:53:47,017 - ai_analysis: {json.dumps({'analysis': {'is_distracted': True, 'reason': 'Its bloody YouTube, mate.'}, 'token_usage': {}, 'analysis_type': 'window_title'})}\n")
            
            # Sample data for yesterday
            f.write(f"{fixed_yesterday_example_date} 10:00:00,000 - window_info: {json.dumps({'window_title': 'Outlook', 'process_name': 'outlook.exe', 'active_time': 1200, 'pid': 1000, 'timestamp': f'{fixed_yesterday_example_date}T10:00:00.000000'})}\n")
            f.write(f"{fixed_yesterday_example_date} 10:00:00,000 - ai_analysis: {json.dumps({'analysis': {'is_distracted': False, 'reason': 'Work email.'}, 'token_usage': {}, 'analysis_type': 'window_title'})}\n")
            f.write(f"{fixed_yesterday_example_date} 11:00:00,000 - window_durations: {json.dumps({'Outlook': {'total': 3600000, 'consecutive': 0}, 'Excel.exe': {'total': 1800000, 'consecutive': 0}})}\n")
            app.logger.info(f"Created dummy log file at {LOG_FILE_PATH}")

    app.run(debug=True)
