import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import folium
from folium.plugins import HeatMap
import argparse
from geopy.distance import geodesic

def load_coordinates(filename):
    data = pd.read_csv(filename)
    return data['latitude'].values, data['longitude'].values

def calculate_center(latitudes, longitudes):
    center_lat = np.mean(latitudes)
    center_lon = np.mean(longitudes)
    return center_lat, center_lon

def calculate_furthest_distance(latitudes, longitudes, center_lat, center_lon):
    distances = [geodesic((lat, lon), (center_lat, center_lon)).meters for lat, lon in zip(latitudes, longitudes)]
    return max(distances)

def plot_histogram_heatmap(latitudes, longitudes, grid_size=5000):
    histogram, xedges, yedges = np.histogram2d(longitudes, latitudes, bins=grid_size)
    histogram = np.log1p(histogram)  # Log scaling to enhance visibility of lower densities

    plt.figure(figsize=(12, 10))
    plt.imshow(np.rot90(histogram), cmap='hot', extent=[xedges.min(), xedges.max(), yedges.min(), yedges.max()])
    plt.colorbar(label='Log(Count + 1)')
    plt.title("2D Histogram Heatmap")
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.show()

    return histogram, xedges, yedges

def find_coldest_point(histogram, xedges, yedges):
    # Identify the bin with the lowest count greater than 0
    min_count = np.min(histogram[np.nonzero(histogram)])
    coldest_idx = np.where(histogram == min_count)
    coldest_lat = yedges[coldest_idx[0]][0] + (yedges[1] - yedges[0]) / 2
    coldest_lon = xedges[coldest_idx[1]][0] + (xedges[1] - xedges[0]) / 2
    return coldest_lat, coldest_lon

def overlay_histogram_on_map(histogram, xedges, yedges, latitudes, longitudes, coldest_point):
    m = folium.Map(location=[np.mean(latitudes), np.mean(longitudes)], zoom_start=10)
    heatmap_data = [[yedges[i] + (yedges[i+1]-yedges[i])/2, xedges[j] + (xedges[j+1]-xedges[j])/2, histogram[i][j]]
                    for i in range(len(yedges)-1) for j in range(len(xedges)-1) if histogram[i][j] > 0]
    HeatMap(heatmap_data, min_opacity=0.5, max_opacity=0.8, radius=15).add_to(m)
    folium.Marker(coldest_point, popup='Coldest Point', icon=folium.Icon(color='blue', icon='snowflake')).add_to(m)
    m.save('histogram_heatmap.html')
    print("Heatmap saved to 'histogram_heatmap.html'.")

def main():
    parser = argparse.ArgumentParser(description="Generate a 2D histogram heatmap from geographic data points and identify the coldest point.")
    parser.add_argument("filename", type=str, help="CSV file containing latitude and longitude columns")
    args = parser.parse_args()

    latitudes, longitudes = load_coordinates(args.filename)
    histogram, xedges, yedges = plot_histogram_heatmap(latitudes, longitudes)
    coldest_point = find_coldest_point(histogram, xedges, yedges)
    overlay_histogram_on_map(histogram, xedges, yedges, latitudes, longitudes, coldest_point)

if __name__ == '__main__':
    main()
