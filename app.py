import json
import os
from flask import Flask, render_template, request
from datetime import datetime, timedelta
from collections import defaultdict
import pytz # For timezone handling, if needed in the future

app = Flask(__name__)

# --- Helper Functions ---
def format_timedelta(td):
    """Formats a timedelta object into a human-readable string (Xh Ym Zs)."""
    if td is None:
        return "N/A"
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts) if parts else "0s"

def format_datetime_obj(dt_obj, format_str='%Y-%m-%d %H:%M:%S'):
    """Formats a datetime object to a string."""
    if dt_obj is None:
        return "N/A"
    return dt_obj.strftime(format_str)

def load_and_process_data(filepath, selected_date_str=None):
    """Loads and processes the activity log data for a selected date."""
    try:
        with open(filepath, 'r') as f:
            all_logs_raw = json.load(f)
    except FileNotFoundError:
        return {"error": "Data file not found. Please create logs/activity_data.json"}
    except json.JSONDecodeError:
        return {"error": "Error decoding JSON data. Please check the file format."}

    if not isinstance(all_logs_raw, list):
        return {"error": "Data should be a list of log entries."}

    # Parse all logs and extract available dates
    parsed_logs = []
    available_dates = set()
    for log_raw in all_logs_raw:
        try:
            ts_obj = datetime.fromisoformat(log_raw['timestamp'])
            parsed_logs.append({**log_raw, 'timestamp_obj': ts_obj})
            available_dates.add(ts_obj.strftime('%Y-%m-%d'))
        except (KeyError, TypeError, ValueError) as e:
            # Skip logs with invalid timestamps but log an issue (optional)
            print(f"Skipping log due to timestamp error: {e} in {log_raw}") # Server-side log
            continue
    
    sorted_available_dates = sorted(list(available_dates), reverse=True)

    if not parsed_logs:
        return {
            "error": "No valid log entries found in the data file.",
            "available_dates": [],
            "current_selected_date": "N/A"
        }

    # Determine current selected date
    if selected_date_str and selected_date_str in available_dates:
        current_selected_date = selected_date_str
    elif sorted_available_dates:
        current_selected_date = sorted_available_dates[0] # Default to the latest date with data
    else: # Should not happen if parsed_logs is not empty, but as a fallback
        current_selected_date = datetime.now().strftime('%Y-%m-%d') # Fallback to actual today

    # Filter logs for the selected date
    logs_for_day = [log for log in parsed_logs if log['timestamp_obj'].strftime('%Y-%m-%d') == current_selected_date]
    logs_for_day.sort(key=lambda x: x['timestamp_obj']) # Ensure logs for the day are sorted

    # --- Initialize variables for daily data ---
    focus_sessions = []
    app_usage_data = defaultdict(lambda: defaultdict(timedelta))
    distractions = []
    timeline_events = []
    total_focus_duration = timedelta()
    total_screen_time = timedelta()
    day_start_time = None
    day_end_time = None

    if logs_for_day:
        day_start_time = logs_for_day[0]['timestamp_obj']
        day_end_time = logs_for_day[-1]['timestamp_obj']

        # --- Process Focus Sessions for the day ---
        current_focus_session = None
        for log in logs_for_day:
            timestamp = log['timestamp_obj']
            if log['type'] == 'focus_mode_start':
                current_focus_session = {
                    'start': timestamp,
                    'description': log.get('data', {}).get('description', 'No description')
                }
            elif log['type'] == 'focus_mode_end' and current_focus_session:
                # Ensure the focus session started on the same day or before, and ended on this day
                if current_focus_session['start'].strftime('%Y-%m-%d') <= current_selected_date:
                    current_focus_session['end'] = timestamp
                    duration = current_focus_session['end'] - current_focus_session['start']
                    current_focus_session['duration'] = duration
                    current_focus_session['duration_str'] = format_timedelta(duration)
                    total_focus_duration += duration
                    focus_sessions.append(current_focus_session)
                current_focus_session = None 
        # If a focus session is still active at the end of the day's logs (or data)
        if current_focus_session and current_focus_session['start'].strftime('%Y-%m-%d') == current_selected_date:
             # Optionally, mark as ongoing or calculate duration up to day_end_time
             # For simplicity, we'll only count fully ended sessions within the day or those ending on the day.
             pass


        # --- Process Application Usage for the day ---
        for i in range(len(logs_for_day) -1):
            current_log = logs_for_day[i]
            next_log = logs_for_day[i+1]
            if current_log['type'] == 'window_info':
                try:
                    start_time = current_log['timestamp_obj']
                    end_time = next_log['timestamp_obj']
                    duration = end_time - start_time
                    if duration > timedelta(seconds=0):
                        data = current_log.get('data', {})
                        process_name = data.get('process_name', 'Unknown Process')
                        window_title = data.get('window_title', 'Unknown Title')
                        app_usage_data[process_name][window_title] += duration
                        total_screen_time += duration
                except (KeyError, TypeError, ValueError):
                    continue
        
        # --- Process AI Analysis for Distractions for the day ---
        for i, log in enumerate(logs_for_day):
            if log['type'] == 'ai_analysis':
                analysis_data = log.get('data', {}).get('analysis', {})
                if analysis_data.get('is_distracted', False):
                    window_title, process_name = "N/A", "N/A"
                    for j in range(i - 1, -1, -1):
                        if logs_for_day[j]['type'] == 'window_info':
                            window_data = logs_for_day[j].get('data', {})
                            window_title = window_data.get('window_title', 'N/A')
                            process_name = window_data.get('process_name', 'N/A')
                            break
                    distractions.append({
                        'timestamp': format_datetime_obj(log['timestamp_obj']),
                        'reason': analysis_data.get('reason', 'No reason provided'),
                        'timeout': analysis_data.get('timeout', 0),
                        'window_title': window_title,
                        'process_name': process_name,
                        'analysis_type': log.get('data', {}).get('analysis_type', 'N/A'),
                        'token_usage': log.get('data', {}).get('token_usage', {})
                    })

        # --- Create Timeline Events for the day ---
        for log_entry in logs_for_day:
            ts_str = format_datetime_obj(log_entry['timestamp_obj'])
            event_type = log_entry['type'].replace('_', ' ').title()
            details, data = "", log_entry.get('data', {})
            if log_entry['type'] == 'focus_mode_start': details = f"Desc: {data.get('description', 'N/A')}"
            elif log_entry['type'] == 'focus_mode_end': details = "Focus session ended."
            elif log_entry['type'] == 'window_info': details = f"App: {data.get('process_name', 'N/A')} - Title: {data.get('window_title', 'N/A')}"
            elif log_entry['type'] == 'ai_analysis':
                analysis = data.get('analysis', {})
                status = "Distracted" if analysis.get('is_distracted') else "Not Distracted"
                reason = analysis.get('reason', '')
                details = f"Status: {status}. Reason: {reason[:100]}{'...' if len(reason) > 100 else ''}"
            timeline_events.append({'timestamp_str': ts_str, 'type': event_type, 'details': details})

    # --- Prepare app_usage_detailed for the template (for the selected day) ---
    app_usage_detailed = []
    all_app_total_seconds_today = []
    for process_name, titles_data in app_usage_data.items():
        app_total_duration_obj = timedelta()
        processed_titles = []
        for window_title, duration_obj in titles_data.items():
            app_total_duration_obj += duration_obj
            processed_titles.append({
                'title': window_title,
                'duration_str': format_timedelta(duration_obj),
                'duration_seconds': int(duration_obj.total_seconds())
            })
        processed_titles.sort(key=lambda x: x['duration_seconds'], reverse=True)
        app_total_seconds_val = int(app_total_duration_obj.total_seconds())
        if app_total_seconds_val > 0:
            all_app_total_seconds_today.append(app_total_seconds_val)
            app_usage_detailed.append({
                'name': process_name,
                'total_duration_str': format_timedelta(app_total_duration_obj),
                'total_duration_seconds': app_total_seconds_val,
                'titles': processed_titles
            })
    app_usage_detailed.sort(key=lambda x: x['total_duration_seconds'], reverse=True)
    max_overall_duration_seconds_today = max(all_app_total_seconds_today) if all_app_total_seconds_today else 1

    summary_stats = {
        'total_focus_duration_str': format_timedelta(total_focus_duration),
        'total_screen_time_str': format_timedelta(total_screen_time),
        'total_distractions': len(distractions),
        'day_start_time_str': format_datetime_obj(day_start_time, '%H:%M:%S') if day_start_time else "N/A",
        'day_end_time_str': format_datetime_obj(day_end_time, '%H:%M:%S') if day_end_time else "N/A",
    }

    return {
        'focus_sessions': sorted(focus_sessions, key=lambda x: x['start'], reverse=True),
        'app_usage_detailed': app_usage_detailed,
        'max_overall_duration_seconds': max_overall_duration_seconds_today,
        'distractions': sorted(distractions, key=lambda x: x['timestamp'], reverse=True),
        'summary_stats': summary_stats,
        'timeline_events': timeline_events, # Already sorted by timestamp for the day
        'available_dates': sorted_available_dates,
        'current_selected_date': current_selected_date
    }

@app.route('/')
def index():
    data_filepath = os.path.join(os.path.dirname(__file__), 'logs', 'activity_data.json')
    selected_date_str = request.args.get('date') # Get date from URL query parameter
    
    processed_data = load_and_process_data(data_filepath, selected_date_str)

    if "error" in processed_data and processed_data["error"] not in ["No valid log entries found in the data file."]: # Allow "no logs" error to render page
        return render_template('error.html', message=processed_data["error"])
        
    return render_template('index.html', **processed_data)

if __name__ == '__main__':
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        print(f"Created directory: {logs_dir}")

    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
        print(f"Created directory: {templates_dir}")
        # Basic error.html (ensure it uses Space Mono too if you want consistency)
        with open(os.path.join(templates_dir, 'error.html'), 'w') as f:
            f.write("""
            <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Error</title><script src="https://cdn.tailwindcss.com"></script>
            <link href="https://fonts.googleapis.com/css2?family=Space+Mono&display=swap" rel="stylesheet">
            <style> body { font-family: 'Space Mono', monospace; background-color: #111827; color: #e5e7eb; } </style></head>
            <body class="flex items-center justify-center min-h-screen"><div class="bg-red-800 p-8 rounded-lg shadow-xl text-center">
            <h1 class="text-4xl mb-4">Error</h1><p class="text-xl">{{ message }}</p>
            <a href="/" class="mt-6 inline-block bg-yellow-400 text-black px-6 py-2 rounded hover:bg-yellow-500">Go Home</a>
            </div></body></html>
            """)
    app.run(debug=True)
