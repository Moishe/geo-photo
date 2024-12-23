import numpy as np
from scipy.optimize import minimize, differential_evolution
import folium
import argparse
import csv
import random
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPolygon
from geopy.geocoders import Nominatim
import overpass
from shapely.geometry import shape, mapping

# Initialize the geocoder
geolocator = Nominatim(user_agent="geo_boundary_locator")

# Haversine formula to calculate distance between two lat-long coordinates
def haversine(coord1, coord2):
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    R = 6371  # Earth radius in kilometers

    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2 +
         np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) *
         np.sin(dlon / 2) ** 2)
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    distance = R * c
    return distance

# Get the boundary of the specified geographic level containing the center coordinates
def get_boundary(center_lat, center_lon, level):
    location = geolocator.reverse((center_lat, center_lon), exactly_one=True)
    if not location:
        raise ValueError("Could not determine the location for the given coordinates.")

    address = location.raw.get("address", {})
    if level not in address:
        raise ValueError(f"The specified level '{level}' was not found in the address.")

    # Get the name of the geographic area at the specified level
    area_name = address.get(level)
    country = address.get('country', '')
    state = address.get('state', '')

    # Debug: Print location details
    print(f"Location details: {location.raw}")
    print(f"Area name for level '{level}': {area_name}")

    # Use Overpass API to get the boundary of the area
    api = overpass.API()
    query = f'relation["name"="{area_name}"]["boundary"="administrative"]["type"="boundary"]["admin_level"];out geom;'
    response = api.get(query, responseformat="json")

    # Debug: Print Overpass API response
    print(f"Overpass API response: {response}")

    if 'elements' not in response or len(response['elements']) == 0:
        raise ValueError(f"Could not find geographic boundary for the level '{level}' and area '{area_name}'.")

    # Extract the geometry and handle possible MultiPolygon or Polygon types
    geometries = []
    for element in response['elements']:
        if 'geometry' in element:
            coords = [[(p['lon'], p['lat']) for p in element['geometry']]]
            if element['type'] == 'relation':
                geometries.append(Polygon(coords[0]))
            elif element['type'] == 'way':
                geometries.append(Polygon(coords[0]))
    
    if not geometries:
        raise ValueError(f"No valid geometry found for '{area_name}'.")
    
    # Combine geometries if necessary
    if len(geometries) == 1:
        return geometries[0]
    else:
        return MultiPolygon(geometries)

# Objective function to maximize the minimum distance to any point in the set and the given boundary
def objective_function(x, points, boundary):
    test_point = Point(x[0], x[1])
    if not boundary.contains(test_point):
        return 1000000000  # Penalize points outside the boundary with a large penalty value

    distances = [haversine(x, p) for p in points]
    weighted_distances = [1.0 / dist for dist in distances]
    return sum(weighted_distances)

# Read coordinates from file
def read_coordinates_from_file(file_path):
    points = []
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header
        for row in reader:
            lat, lon = float(row[0]), float(row[1])
            if -90 <= lat <= 90 and -180 <= lon <= 180:  # Filter out invalid coordinates
                points.append((lat, lon))
    return points

# Precompute optimal points within the geographic boundary
def precompute_optimal_points(points, boundary):
    optimal_points = {}
    bounds = [(boundary.bounds[0], boundary.bounds[2]), (boundary.bounds[1], boundary.bounds[3])]  # Bounding box of the boundary
    with open("optimal_points.csv", "w") as csv_file:
        csv_file.write("latitude,longitude,google_maps_link,gaia_gps_link\n")

        # Differential evolution for better global optimization
        result = differential_evolution(objective_function, bounds, args=(points, boundary),
                                        strategy='best1bin', maxiter=1000, popsize=15, tol=1e-6)
        if result.success:
            optimal_points = result.x
            lat, lon = result.x
            google_maps_link = f"https://www.google.com/maps?q={lat},{lon}"
            gaia_gps_link = f"https://www.gaiagps.com/map/?lat={lat}&lon={lon}&zoom=15"
            csv_file.write(f"{lat:.6f},{lon:.6f},{google_maps_link},{gaia_gps_link}\n")
            csv_file.flush()
        else:
            print(f"Optimization failed: {result.message}")
    return optimal_points

# Plot maps with optimal points
def plot_maps(points, optimal_point, boundary):
    # Create a map centered around the optimal point
    folium_map = folium.Map(location=[optimal_point[0], optimal_point[1]], zoom_start=12)

    # Plot all points as dark green dots
    for point in points:
        folium.CircleMarker(location=point, radius=1, color='darkgreen', fill=True, fill_color='darkgreen').add_to(folium_map)

    # Plot the optimal point as a red dot
    folium.Marker(location=optimal_point, icon=folium.Icon(color='red'),
                  popup=folium.Popup('<a href="https://www.google.com/maps?q={0},{1}" target="_blank">View on Google Maps</a>'.format(*optimal_point), max_width=300)).add_to(folium_map)

    # Plot the geographic boundary
    folium.GeoJson(boundary, style_function=lambda x: {'color': 'green', 'fill': False}).add_to(folium_map)

    # Save the map HTML to a file
    folium_map.save("optimal_point_map.html")

# Main function
def main():
    parser = argparse.ArgumentParser(description="Find the optimal point within a geographic area that is furthest from a set of coordinates.")
    parser.add_argument("file_path", type=str, help="Path to the CSV file containing coordinates.")
    parser.add_argument("--level", type=str, choices=["city", "county", "state", "country"],
                        help="Geographic level to constrain the search ('city', 'county', 'state', 'country').")
    parser.add_argument("--center_lat", type=float, default=40.050250, help="Latitude of the center point (default: 40.014984).")
    parser.add_argument("--center_lon", type=float, default=-105.247580, help="Longitude of the center point (default: -105.2797).")
    args = parser.parse_args()

    # Read coordinates from file
    points = read_coordinates_from_file(args.file_path)

    # Get the boundary for the specified level
    boundary = get_boundary(args.center_lat, args.center_lon, args.level)

    # Precompute the optimal point within the boundary
    optimal_point = precompute_optimal_points(points, boundary)

    # Plot the map with the optimal point
    plot_maps(points, optimal_point, boundary)
    print("Map saved as 'optimal_point_map.html'")
    print("CSV file saved as 'optimal_points.csv'")

if __name__ == "__main__":
    main()
