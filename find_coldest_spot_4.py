import numpy as np
import matplotlib.pyplot as plt
import folium
from folium import plugins
import pandas as pd
import branca.colormap as cm
import argparse
from geopy.distance import geodesic
import math

def load_coordinates(filename):
    data = pd.read_csv(filename)
    latitudes = data['latitude'].values
    longitudes = data['longitude'].values
    return latitudes, longitudes

def meters_to_latlong(lat, lon, meters):
    dest = geodesic(meters=meters).destination((lat, lon), 0)
    return abs(dest.latitude - lat), abs(dest.longitude - lon)

def create_grid(latitudes, longitudes, unit_size, center_lat, center_lon, radius_meters):
    lat_min, lat_max = min(latitudes), max(latitudes)
    lon_min, lon_max = min(longitudes), max(longitudes)
    grid_height = int((lat_max - lat_min) / unit_size) + 1
    grid_width = int((lon_max - lon_min) / unit_size) + 1
    grid = np.zeros((grid_height, grid_width))
    center_row = int((center_lat - lat_min) / unit_size)
    center_col = int((center_lon - lon_min) / unit_size)
    return grid, lat_min, lon_min, grid_height, grid_width, center_row, center_col, radius_meters

def apply_points_to_grid(grid, latitudes, longitudes, lat_min, lon_min, unit_size, influence_meters, max_distance_cells):
    height, width = grid.shape
    influence_latlong = meters_to_latlong(lat_min, lon_min, influence_meters)
    for lat, lon in zip(latitudes, longitudes):
        row = int((lat - lat_min) / unit_size)
        col = int((lon - lon_min) / unit_size)
        for i in range(max(-row, -max_distance_cells), min(height - row, max_distance_cells + 1)):
            for j in range(max(-col, -max_distance_cells), min(width - col, max_distance_cells + 1)):
                distance = math.sqrt(i**2 + j**2) * unit_size / max(influence_latlong)
                if distance <= 1:
                    decay = 1 - distance
                    grid[row + i, col + j] += decay if decay > 0 else 0

def find_coldest_point(grid, center_row, center_col, radius_meters, unit_size, lat_min, lon_min):
    best_value = float('inf')
    best_pos = (None, None)
    radius_latlong = meters_to_latlong(lat_min, lon_min, radius_meters)
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            if grid[i][j] > 0:
                distance = math.sqrt((center_row - i) ** 2 + (center_col - j) ** 2) * unit_size / max(radius_latlong)
                if distance <= 1:
                    if grid[i][j] < best_value:
                        best_value = grid[i][j]
                        best_pos = (i, j)
    if best_pos == (None, None):
        return None
    row, col = best_pos
    lat = lat_min + (row + 0.5) * unit_size
    lon = lon_min + (col + 0.5) * unit_size
    return (lat, lon)

def display_grid(grid):
    plt.figure(figsize=(10, 10))
    plt.imshow(grid, cmap='coolwarm', origin='lower')
    plt.colorbar(label='Value')
    plt.title('Heatmap of Grid Values')
    plt.xlabel('Longitude Index')
    plt.ylabel('Latitude Index')
    plt.show()

def overlay_grid_on_map(grid, lat_min, lon_min, unit_size, coldest_point):
    height, width = grid.shape
    lat_max = lat_min + height * unit_size
    lon_max = lon_min + width * unit_size
    m = folium.Map(location=[(lat_min + lat_max) / 2, (lon_min + lon_max) / 2], zoom_start=13)
    colormap = cm.linear.YlOrRd_09.scale(0, grid.max())
    m.add_child(colormap)
    for i in range(height):
        for j in range(width):
            if grid[i][j] > 0:
                folium.Rectangle(
                    bounds=[
                        [lat_min + i * unit_size, lon_min + j * unit_size],
                        [lat_min + (i + 1) * unit_size, lon_min + (j + 1) * unit_size]
                    ],
                    color=colormap(grid[i][j]),
                    fill=True,
                    fill_color=colormap(grid[i][j]),
                    fill_opacity=0.6
                ).add_to(m)
    if coldest_point:
        folium.Marker(
            location=coldest_point,
            popup="Coldest Point",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)
    return m

def main():
    parser = argparse.ArgumentParser(description='Process lat-long points to find the coldest spot.')
    parser.add_argument('filename', type=str, help='CSV file containing latitude and longitude columns')
    parser.add_argument('center_lat', type=float, help='Latitude of the center point')
    parser.add_argument('center_lon', type=float, help='Longitude of the center point')
    parser.add_argument('radius', type=float, help='Radius in meters to include for coldest point calculation')
    parser.add_argument('influence_radius', type=float, help='Radius in meters at which the influence of a point runs out')
    args = parser.parse_args()

    latitudes, longitudes = load_coordinates(args.filename)
    unit_size = 0.01  # Define unit size

    grid, lat_min, lon_min, grid_height, grid_width, center_row, center_col, radius_meters = create_grid(latitudes, longitudes, unit_size, args.center_lat, args.center_lon, args.radius)
    max_distance_cells = int(args.influence_radius / (geodesic(meters=args.influence_radius).destination((args.center_lat, args.center_lon), 90).longitude - args.center_lon) / unit_size)
    apply_points_to_grid(grid, latitudes, longitudes, lat_min, lon_min, unit_size, args.influence_radius, max_distance_cells)
    coldest_point = find_coldest_point(grid, center_row, center_col, radius_meters, unit_size, lat_min, lon_min)

    if coldest_point:
        print(f"Coldest point (latitude, longitude): {coldest_point}")
        display_grid(grid)
        m = overlay_grid_on_map(grid, lat_min, lon_min, unit_size, coldest_point)
        m.save('map.html')  # Save the map to an HTML file
    else:
        print("No valid coldest point found within the specified radius.")

if __name__ == '__main__':
    main()
