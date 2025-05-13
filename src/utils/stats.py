import collections
from datetime import datetime, timedelta, timezone
from datetime import datetime, timezone, timedelta # Add timedelta if not already imported at class/module level
from dateutil import tz # For robust local timezone detection

class UserStats:
    def __init__(self, logger):
        self.logger = logger
        self.window_instance_duration_sec = 1
    
    def _parse_timestamp_to_utc(self, timestamp_str: str) -> datetime | None:
        if not isinstance(timestamp_str, str):
            return None
        try:
            # If timestamp string ends with 'Z', replace it with '+00:00' for fromisoformat
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            
            dt_obj = datetime.fromisoformat(timestamp_str)
            
            # Check if the datetime object is naive (no timezone info)
            if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
                # Timestamp is naive. Assume it's in the system's local timezone.
                local_timezone = tz.gettz() # Get system's local timezone
                if local_timezone:
                    dt_obj = dt_obj.replace(tzinfo=local_timezone) # Assign local timezone
                    dt_obj = dt_obj.astimezone(timezone.utc) # Convert to UTC
                else:
                    # Fallback: if local timezone can't be determined, assume UTC with a warning.
                    # This case is unlikely with dateutil but good for robustness.
                    print("Warning: Could not determine local timezone. Assuming naive timestamps are UTC.")
                    dt_obj = dt_obj.replace(tzinfo=timezone.utc)
            else:
                # Timestamp is already timezone-aware, just ensure it's UTC.
                dt_obj = dt_obj.astimezone(timezone.utc)
            return dt_obj
        except ValueError:
            print(f"Debug: Failed to parse timestamp string with fromisoformat: {timestamp_str}")
            return None

    # ... (rest of your get_most_used_windows function, it should now work correctly with the updated parser)
    # Make sure to keep the debug prints for now, or remove them once you confirm it's working.
    def get_most_used_windows(self, mins_ago: int = 10, count: int = 3):
        all_logs = self.logger.get_logs()
        if not all_logs:
            # print("Debug: No logs returned by logger.get_logs().") # Kept for example
            return []

        now_utc = datetime.now(timezone.utc)
        time_filter_start_utc = now_utc - timedelta(minutes=mins_ago)

        all_parsed_window_events = []
        for log_entry in all_logs:
            if not isinstance(log_entry, dict) or log_entry.get("type") != "window_info":
                continue
            data = log_entry.get("data")
            if not isinstance(data, dict):
                continue
            timestamp_str = data.get("timestamp")
            parsed_ts_utc = self._parse_timestamp_to_utc(timestamp_str) # Uses updated parser
            if not parsed_ts_utc:
                # print(f"Debug: Skipped log due to unparsable timestamp: {timestamp_str}")
                continue
            window_title = data.get("window_title")
            process_name = data.get("process_name")
            if window_title is None or process_name is None:
                continue
            all_parsed_window_events.append({
                "parsed_timestamp": parsed_ts_utc,
                "window_title": window_title,
                "process_name": process_name
            })

        if not all_parsed_window_events:
            # print("Debug: all_parsed_window_events is empty after processing logs.")
            return []
        
        all_parsed_window_events.sort(key=lambda x: x["parsed_timestamp"], reverse=True)
        # Optional: print for verification after fix
        # print(f"Debug (Post-Fix): Sample of latest parsed event (UTC): {all_parsed_window_events[0]['parsed_timestamp']}")
        # print(f"Debug (Post-Fix): Current time (now_utc): {now_utc}")
        # print(f"Debug (Post-Fix): Filtering events that occurred after (time_filter_start_utc): {time_filter_start_utc}")


        last_overall_window_event = all_parsed_window_events[0]
        
        recent_window_events_for_aggregation = [
            event for event in all_parsed_window_events if event["parsed_timestamp"] >= time_filter_start_utc
        ]
        
        # Optional: print for verification after fix
        # print(f"Debug (Post-Fix): Found {len(recent_window_events_for_aggregation)} events for aggregation after time filtering.")


        if not recent_window_events_for_aggregation:
            return []

        # Using collections.defaultdict, so ensure it's imported
        # import collections (if not already at the top of the file)
        window_usage_counts = collections.defaultdict(int) # Ensure collections is imported
        for event in recent_window_events_for_aggregation:
            key = (event["window_title"], event["process_name"])
            window_usage_counts[key] += 1
        
        processed_windows = []
        for (title, process), num_instances in window_usage_counts.items():
            active_time_seconds = num_instances * self.window_instance_duration_sec
            is_still_active = False
            if last_overall_window_event:
                matches_last_event = (
                    title == last_overall_window_event["window_title"] and
                    process == last_overall_window_event["process_name"]
                )
                if matches_last_event:
                    time_since_last_event_log_seconds = (now_utc - last_overall_window_event["parsed_timestamp"]).total_seconds()
                    if 0 <= time_since_last_event_log_seconds <= 2:
                        is_still_active = True
            processed_windows.append({
                "window_title": title,
                "process_name": process,
                "active_time": active_time_seconds,
                "still_active": is_still_active
            })

        processed_windows.sort(key=lambda x: (-x["active_time"], x["window_title"], x["process_name"]))
        return processed_windows[:count]