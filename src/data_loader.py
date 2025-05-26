import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

def group_nearby_coordinates(df, distance_threshold_meters=30.0):
    unique_coords = df[['lat', 'lng']].drop_duplicates().reset_index(drop=True)
    coords_rad = np.radians(unique_coords[['lat', 'lng']].values)
    earth_radius = 6371000
    eps_radians = distance_threshold_meters / earth_radius
    
    dbscan = DBSCAN(eps=eps_radians, min_samples=1, metric='haversine')
    cluster_labels = dbscan.fit_predict(coords_rad)
    unique_coords['coordinate_group_id'] = cluster_labels
    
    grouped_coords = unique_coords.groupby('coordinate_group_id').agg({
        'lat': 'mean',
        'lng': 'mean'
    }).reset_index()
    grouped_coords.columns = ['coordinate_group_id', 'group_lat', 'group_lng']
    
    unique_coords = unique_coords.merge(grouped_coords, on='coordinate_group_id')
    
    result_df = df.merge(
        unique_coords[['lat', 'lng', 'group_lat', 'group_lng', 'coordinate_group_id']], 
        on=['lat', 'lng'], 
        how='left'
    )
    
    return result_df

def load_and_prepare_visualization_data(events_parquet_path, group_coordinates=True, distance_threshold_meters=30.0):
    events_data = pd.read_parquet(events_parquet_path)
    
    required_columns = ['event_type', 'minute', 'lat', 'lng', 'bike_type', 'time_window']
    missing_columns = [col for col in required_columns if col not in events_data.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    processed_data = events_data.copy()
    
    if group_coordinates and 'group_lat' not in processed_data.columns:
        processed_data = group_nearby_coordinates(processed_data, distance_threshold_meters)
    
    start_data = processed_data[processed_data.event_type == 'start'].copy()
    end_data = processed_data[processed_data.event_type == 'end'].copy()
    
    return processed_data, start_data, end_data

def filter_data_for_time_window(start_data, end_data, time_window, bike_type='all'):
    start_filtered = start_data[start_data.time_window == time_window].copy()
    end_filtered = end_data[end_data.time_window == time_window].copy()
    
    if bike_type != 'all':
        start_filtered = start_filtered[start_filtered.bike_type == bike_type]
        end_filtered = end_filtered[end_filtered.bike_type == bike_type]
    
    return start_filtered, end_filtered

def standardize_numerical_columns(df, numerical_columns):
    scaler = StandardScaler()
    df[numerical_columns] = scaler.fit_transform(df[numerical_columns])
    return df

def one_hot_encode_categorical_columns(df, categorical_columns):
    df = pd.get_dummies(df, columns=categorical_columns, drop_first=True)
    return df

def preprocess_data(events_data, group_coordinates=True, distance_threshold_meters=30.0):
    processed_data = events_data.copy()
    
    if group_coordinates and 'group_lat' not in processed_data.columns:
        processed_data = group_nearby_coordinates(processed_data, distance_threshold_meters)
    
    processed_data = standardize_numerical_columns(processed_data, ['lat', 'lng'])
    processed_data = one_hot_encode_categorical_columns(processed_data, ['event_type', 'bike_type', 'time_window'])
    
    return processed_data

def load_and_preprocess_data(events_parquet_path, group_coordinates=True, distance_threshold_meters=30.0):
    events_data = pd.read_parquet(events_parquet_path)
    processed_data = preprocess_data(events_data, group_coordinates, distance_threshold_meters)
    
    return processed_data
