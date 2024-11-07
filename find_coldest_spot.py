import numpy as np
import matplotlib.pyplot as plt
import folium
from folium import plugins
import pandas as pd

def load_coordinates(filename):
    data = pd.read_csv(filename)
    latitudes = data['latitude'].values
    longitudes = data['longitude'].values
    return latitudes, longitudes

def create_grid(latitudes, longitudes, unit_size):
    lat_min, lat_max = min(latitudes), max(latitudes)
    lon_min, lon_max = min(longitudes), max(longitudes)
    grid_height = int((lat_max - lat_min) / unit_size) + 1
    grid_width = int((lon_max - lon_min) / unit_size) + 1
    grid = np.zeros((grid_height, grid_width))
    return grid, lat_min, lon_min, grid_height, grid_width

def apply_points_to_grid(grid, latitudes, longitudes, lat_min, lon_min, unit_size, max_distance=10):
    height, width = grid.shape
    for lat, lon in zip(latitudes, longitudes):
        row = int((lat - lat_min) / unit_size)
        col = int((lon - lon_min) / unit_size)
        for i in range(max(-row, -max_distance), min(height - row, max_distance + 1)):
            for j in range(max(-col, -max_distance), min(width - col, max_distance + 1)):
                distance = np.sqrt(i**2 + j**2)
                if distance <= max_distance:
                    grid[row + i, col + j] += 1 / (2 ** int(distance))

def find_coldest_point(grid, lat_min, lon_min, unit_size):
    coldest_idx = np.unravel_index(np.argmin(grid, axis=None), grid.shape)
    row, col = coldest_idx
    coldest_lat = lat_min + (row + 0.5) * unit_size
    coldest_lon = lon_min + (col + 0.5) * unit_size
    return (coldest_lat, coldest_lon)

def display_grid(grid):
    plt.figure(figsize=(10, 10))
    plt.imshow(grid, cmap='coolwarm', origin='lower')
    plt.colorbar(label='Value')
    plt.title('Heatmap of Grid Values')
    plt.xlabel('Longitude Index')
    plt.ylabel('Latitude Index')
    plt.show()

def overlay_grid_on_map(grid, lat_min, lon_min, unit_size):
    height, width = grid.shape
    lat_max = lat_min + height * unit_size
    lon_max = lon_min + width * unit_size
    m = folium.Map(location=[(lat_min + lat_max) / 2, (lon_min + lon_max) / 2], zoom_start=13)
    heatmap_data = [
        [lat_min + i * unit_size, lon_min + j * unit_size, grid[i][j]]
        for i in range(height) for j in range(width) if grid[i][j] > 0
    ]
    plugins.HeatMap(heatmap_data, min_opacity=0.5, max_val=grid.max()).add_to(m)
    return m

# Example usage
filename = 'photo_coordinates_deduped.csv'  # CSV file with latitude and longitude
latitudes, longitudes = load_coordinates(filename)
unit_size = 0.01  # Define unit size

grid, lat_min, lon_min, _, _ = create_grid(latitudes, longitudes, unit_size)
apply_points_to_grid(grid, latitudes, longitudes, lat_min, lon_min, unit_size)
coldest_point = find_coldest_point(grid, lat_min, lon_min, unit_size)

print(f"Coldest point (latitude, longitude): {coldest_point}")
display_grid(grid)

m = overlay_grid_on_map(grid, lat_min, lon_min, unit_size)
m.save('map.html')  # Save the map to an HTML file
