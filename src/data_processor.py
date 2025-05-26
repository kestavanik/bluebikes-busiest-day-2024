import pandas as pd
import uuid
import numpy as np
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from src.data_loader import group_nearby_coordinates

def process_clean_to_events(clean_parquet_path, output_parquet_path, group_coordinates=True, distance_threshold_meters=30.0):
    busiest_day_df = pd.read_parquet(clean_parquet_path)
    
    events = pd.concat([
        busiest_day_df.assign(
            event_id  = [str(uuid.uuid4()) for _ in range(len(busiest_day_df))],
            event_time= busiest_day_df["started_at"],
            event_type= "start",
            lat       = busiest_day_df["start_lat"],
            lng       = busiest_day_df["start_lng"],
            bike_type = busiest_day_df["rideable_type"],
            ride_id   = busiest_day_df["ride_id"],
        ),
        busiest_day_df.assign(
            event_id  = [str(uuid.uuid4()) for _ in range(len(busiest_day_df))],
            event_time= busiest_day_df["ended_at"],
            event_type= "end",
            lat       = busiest_day_df["end_lat"],
            lng       = busiest_day_df["end_lng"],
            bike_type = busiest_day_df["rideable_type"],
            ride_id   = busiest_day_df["ride_id"],
        ),
    ], ignore_index=True)

    first_day = events['event_time'].dt.date.min()
    events = events[events['event_time'].dt.date == first_day]

    events["minute"] = events["event_time"].dt.hour * 60 + events["event_time"].dt.minute
    events['time_window'] = events['minute'] // 10
    
    events = events.drop(columns=['rideable_type', 'started_at', 'ended_at', 'start_lat', 
                                'start_lng', 'end_lat', 'end_lng', 'ride_date'], errors='ignore')
    
    if group_coordinates:
        events = group_nearby_coordinates(events, distance_threshold_meters)
    
    columns = ['event_id'] + [col for col in events.columns if col != 'event_id']
    events = events[columns]
    events = events.sort_values('event_time')
    
    events.to_parquet(output_parquet_path, index=False, engine='pyarrow')
    return events

if __name__ == "__main__":
    workspace_root = Path(__file__).resolve().parent.parent
    clean_data_path = workspace_root / "data" / "clean" / "bluebikes_busiest_day.parquet"
    processed_data_path = workspace_root / "data" / "processed" / "bluebikes_events.parquet"
    
    if not clean_data_path.exists():
        raise FileNotFoundError(f"Clean data not found at {clean_data_path}")
    
    process_clean_to_events(clean_data_path, processed_data_path, group_coordinates=True, distance_threshold_meters=30.0)
