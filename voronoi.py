import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon
from scipy.spatial import Voronoi
import numpy as np
import folium
import matplotlib.colors as mcolors

# Load data
data = pd.read_csv('coordinates.csv')
points = [Point(xy) for xy in zip(data.longitude, data.latitude)]
geo_df = gpd.GeoDataFrame(data, geometry=points)

# Convert to a projected CRS for accurate area and distance calculations
geo_df = geo_df.set_crs(epsg=4326)  # WGS 84
geo_df = geo_df.to_crs(epsg=3857)  # Web Mercator

# Extract coordinates for Voronoi calculation
coords = np.array([[point.x, point.y] for point in geo_df.geometry])

# Create Voronoi diagram
vor = Voronoi(coords)

# Create Voronoi Polygons
regions, vertices = vor.regions, vor.vertices
polygons = []
for region in regions:
    if not -1 in region and len(region) > 0:
        polygon = Polygon([vertices[i] for i in region if i >= 0])
        if polygon.area > 0:  # Only consider valid polygons with positive area
            polygons.append(polygon)

# Convert polygons to GeoDataFrame
poly_df = gpd.GeoDataFrame(geometry=polygons)
poly_df = poly_df.set_crs(epsg=3857)  # Set the CRS to match the projected CRS

# Use the constant latlong coordinates for the center point
center_point = Point(-105.25, 40.019444)
center_point = gpd.GeoSeries([center_point], crs=4326).to_crs(epsg=3857).iloc[0]

# Calculate distance of centroids from the center point
poly_df['centroid'] = poly_df.geometry.centroid
poly_df['distance_to_center'] = poly_df.centroid.apply(lambda x: center_point.distance(x))

# Filter polygons whose centroid is within 10 km of the center point for largest polygon calculation
poly_df_within_10km = poly_df[poly_df['distance_to_center'] <= 15000]  # 10 km in meters (since we're in a projected CRS)

# Convert back to WGS 84 for mapping
poly_df = poly_df.to_crs(epsg=4326)
geo_df = geo_df.to_crs(epsg=4326)

# Create a folium map
m = folium.Map(location=[data.latitude.mean(), data.longitude.mean()], zoom_start=10, tiles='OpenStreetMap')

# Add Voronoi polygons to the map with radial gradient approximation
for _, row in poly_df.iterrows():
    polygon = row['geometry']
    centroid = polygon.centroid
    distances = [centroid.distance(Point(coord)) for coord in polygon.exterior.coords]
    max_distance = max(distances)

    # Set color gradient from red at centroid to blue at edge
    colors = []
    for distance in distances:
        ratio = distance / max_distance
        color = mcolors.to_hex((1 - ratio, 0, ratio))  # Red to blue gradient
        colors.append(color)

    # Create GeoJson with gradient color approximation
    sim_geo = gpd.GeoSeries(polygon)
    geo_j = sim_geo.to_json()
    folium.GeoJson(data=geo_j,
                   style_function=lambda x, color=colors[0]: {
                       'fillColor': color,
                       'color': 'black',
                       'weight': 0.5,
                       'fillOpacity': 0.3}).add_to(m)

    # Add a red dot at the centroid of each polygon
    folium.CircleMarker(location=[centroid.y, centroid.x], radius=1, color='red', fill=True, fill_color='red').add_to(m)

# Identify the largest polygon and its centroid within 10 km
largest_poly = poly_df_within_10km.to_crs(epsg=3857).geometry.area.idxmax()
largest_centroid_3857 = poly_df_within_10km.to_crs(epsg=3857).loc[largest_poly].geometry.centroid
largest_centroid = gpd.GeoSeries([largest_centroid_3857], crs=3857).to_crs(epsg=4326).iloc[0]
folium.Marker(location=[largest_centroid.y, largest_centroid.x], popup='Largest Polygon Center').add_to(m)

# Save the map
m.save('voronoi_map.html')
print(f"Largest Polygon Center: {largest_centroid.y}, {largest_centroid.x}")
