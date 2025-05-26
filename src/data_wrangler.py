import pandas as pd
from pathlib import Path

def load_monthly_data(data_dir_path: Path) -> pd.DataFrame:
    csv_files = list(data_dir_path.glob('*.csv'))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir_path}")
    return pd.concat((pd.read_csv(f) for f in csv_files), ignore_index=True)

def preprocess_rides_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop(columns=['start_station_name', 'start_station_id', 'end_station_name', 'end_station_id', 'member_casual'], errors='ignore')
    df = df.astype({
        'ride_id': 'string',
        'rideable_type': 'string',
        'started_at': 'datetime64[ns]',
        'ended_at': 'datetime64[ns]',
        'start_lat': 'float64',
        'start_lng': 'float64',
        'end_lat': 'float64',
        'end_lng': 'float64'
    })
    df['ride_date'] = pd.to_datetime(df['started_at'].dt.date)
    return df

def remove_ride_outliers(df: pd.DataFrame) -> pd.DataFrame:
    ride_duration_seconds = (df['ended_at'] - df['started_at']).dt.total_seconds()
    return df[(ride_duration_seconds > 120) & (ride_duration_seconds < 86400)]

def find_top_busiest_days(df: pd.DataFrame, top_n: int = 10) -> pd.Series:
    return df.groupby('ride_date').size().nlargest(top_n)

def get_rides_for_specific_date(df: pd.DataFrame, date_str: str) -> pd.DataFrame:
    target_date = pd.to_datetime(date_str).date()
    return df[df['ride_date'].dt.date == target_date]

def save_dataframe_to_parquet(df: pd.DataFrame, output_file_path: Path | str):
    df.to_parquet(output_file_path, index=False, engine='pyarrow')

if __name__ == "__main__":
    workspace_root = Path(__file__).resolve().parent
    raw_data_directory = workspace_root / "data" / "raw"
    clean_data_directory = workspace_root / "data" / "clean"
    output_parquet_filename = "bluebikes_busiest_day.parquet"
    output_parquet_path = clean_data_directory / output_parquet_filename

    raw_df = load_monthly_data(raw_data_directory)
    processed_df = preprocess_rides_data(raw_df)
    cleaned_df = remove_ride_outliers(processed_df)
    
    top_busiest_days = find_top_busiest_days(cleaned_df)
    
    if not top_busiest_days.empty:
        busiest_day_date_str = top_busiest_days.index[0].strftime('%Y-%m-%d')
        busiest_day_rides_df = get_rides_for_specific_date(cleaned_df, busiest_day_date_str)
        
        if not busiest_day_rides_df.empty:
            clean_data_directory.mkdir(parents=True, exist_ok=True)
            save_dataframe_to_parquet(busiest_day_rides_df, output_parquet_path)