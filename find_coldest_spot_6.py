import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import folium
from folium.plugins import HeatMap
import argparse
from geopy.distance import geodesic
import math

def load_coordinates(filename):
    data = pd.read_csv(filename)
    print(f"min latitude: {data['latitude'].min()}, max latitude: {data['latitude'].max()}")
    print(f"min longitude: {data['longitude'].min()}, max longitude: {data['longitude'].max()}")
    return data['latitude'].values, data['longitude'].values

def calculate_center(latitudes, longitudes):
    center_lat = np.mean(latitudes)
    center_lon = np.mean(longitudes)
    return center_lat, center_lon

def calculate_furthest_distance(latitudes, longitudes, center_lat, center_lon):
    distances = [geodesic((lat, lon), (center_lat, center_lon)).meters for lat, lon in zip(latitudes, longitudes)]
    return max(distances)

def find_coldest_point(latitudes, longitudes, center_lat, center_lon, max_distance):
    grid_size = 100
    lat_step = max_distance / 2 / 111000  # Convert step to degrees latitude
    coldest_point = None
    max_avg_distance = 0

    for i in range(grid_size + 1):
        for j in range(grid_size + 1):
            test_lat = center_lat - max_distance / 2 / 111000 + lat_step * i
            lon_step = max_distance / 2 / (111000 * math.cos(math.radians(test_lat)))  # Convert step to degrees longitude
            test_lon = center_lon - max_distance / 2 / (111000 * math.cos(math.radians(center_lat))) + lon_step * j

            # Debugging print statement
            print(f"Testing ({test_lat:.6f}, {test_lon:.6f})")

            # Now compute average distance
            distances = [geodesic((lat, lon), (test_lat, test_lon)).meters for lat, lon in zip(latitudes, longitudes)]
            avg_distance = np.mean(distances)
            if avg_distance > max_avg_distance:
                max_avg_distance = avg_distance
                coldest_point = (test_lat, test_lon)

    return coldest_point

def overlay_coldest_point_on_map(latitudes, longitudes, coldest_point):
    m = folium.Map(location=[np.mean(latitudes), np.mean(longitudes)], zoom_start=10)
    folium.Marker(
        location=coldest_point,
        popup=f"Coldest Point: {coldest_point[0]:.6f}, {coldest_point[1]:.6f}",
        icon=folium.Icon(color='blue', icon='snowflake')
    ).add_to(m)
    m.save('map_with_coldest_point.html')
    print("Map with coldest point saved to 'map_with_coldest_point.html'.")

def main():
    parser = argparse.ArgumentParser(description="Find and display the coldest point based on average distance.")
    parser.add_argument("filename", type=str, help="CSV file containing latitude and longitude columns")
    args = parser.parse_args()

    latitudes, longitudes = load_coordinates(args.filename)
    center_lat, center_lon = calculate_center(latitudes, longitudes)
    max_distance = calculate_furthest_distance(latitudes, longitudes, center_lat, center_lon)
    coldest_point = find_coldest_point(latitudes, longitudes, center_lat, center_lon, max_distance)
    overlay_coldest_point_on_map(latitudes, longitudes, coldest_point)

if __name__ == '__main__':
    main()
