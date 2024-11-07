import numpy as np
from scipy.optimize import minimize, differential_evolution
import folium
import argparse
import csv
import random

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

# Objective function to maximize the minimum distance to any point in the set and the given radius,
# while also considering the quantity of points that are close to the given point.
def objective_function(x, points, center, radius):
    distances = [haversine(x, p) for p in points]
    distance_to_center = haversine(x, center)

    #distances = filter(lambda x: x <= (radius / 5.0), distances)

    # Apply penalty if point is outside the bounding circle
    if distance_to_center > radius:
        return 1000000000  # Penalize points outside the bounding radius with a large penalty value

    distance_to_boundary = abs(radius - distance_to_center)
    distances.extend([distance_to_boundary])
    weighted_distances = [1.0/(dist) for dist in distances]
    return sum(weighted_distances)

def read_coordinates_from_file(file_path):
    points = []
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header
        for row in reader:
            points.append((float(row[0]), float(row[1])))
    return points

def precompute_optimal_points(points, center, radius_range, step):
    optimal_points = {}
    bounds = [(center[0] - 0.5, center[0] + 0.5), (center[1] - 0.5, center[1] + 0.5)]  # Adjusted bounds for better exploration
    with open("optimal_points.csv", "w") as csv_file:
        csv_file.write("radius,latitude,longitude,google_maps_link,gaia_gps_link\n")
        for radius in np.arange(radius_range[0], radius_range[1] + step, step):
            radius = round(radius, 2)  # Round radius to avoid floating point issues with IDs

            # Differential evolution for better global optimization
            result = differential_evolution(objective_function, bounds, args=(points, center, radius),
                                            strategy='best1bin', maxiter=1000, popsize=15, tol=1e-6)
            if result.success:
                optimal_points[radius] = result.x
                lat, lon = result.x
                google_maps_link = f"https://www.google.com/maps?q={lat},{lon}"
                gaia_gps_link = f"https://www.gaiagps.com/map/?lat={lat}&lon={lon}&zoom=15"
                csv_file.write(f"{radius},{lat:.6f},{lon:.6f},{google_maps_link},{gaia_gps_link}\n")
                csv_file.flush()
            else:
                print(f"Optimization failed for radius {radius} km: {result.message}")
    return optimal_points

def plot_maps(points, optimal_points, center, radius_range, step):
    maps_html = ""
    for radius, optimal_point in optimal_points.items():
        # Create a map centered around the average of the points
        avg_lat = np.mean([p[0] for p in points])
        avg_lon = np.mean([p[1] for p in points])
        folium_map = folium.Map(location=center, zoom_start=10)

        # Plot all points as dark green dots
        for point in points:
            folium.CircleMarker(location=point, radius=1, color='darkgreen', fill=True, fill_color='darkgreen').add_to(folium_map)

        # Plot the optimal point as a red dot
        folium.Marker(location=optimal_point, icon=folium.Icon(color='red'), popup=folium.Popup('<a href="https://www.google.com/maps?q={0},{1}" target="_blank">View on Google Maps</a>'.format(*optimal_point), max_width=300)).add_to(folium_map)

        # Plot the bounding circle
        folium.Circle(location=center, radius=radius * 1000, color='green', fill=False).add_to(folium_map)

        # Save the map HTML to a string
        map_html = folium_map._repr_html_()
        lat, lon = optimal_point
        google_maps_link = f"https://www.google.com/maps?q={lat},{lon}"
        gaia_gps_link = f"https://www.gaiagps.com/map/?lat={lat}&lon={lon}&zoom=15"
        maps_html += f'<div id="map_{radius:.1f}" style="display:none">{map_html}<br><p>Optimal Point Coordinates: {lat:.6f}, {lon:.6f} - <a href="{google_maps_link}" target="_blank">View on Google Maps</a> - <a href="{gaia_gps_link}" target="_blank">View on GaiaGPS</a></p></div>'

    # Add JavaScript to control visibility
    slider_control_js = f"""
    <script>
    function updateMap(radius) {{
        radius = parseFloat(radius).toFixed(1);  // Ensure radius matches the ID format
        var allMaps = document.querySelectorAll('[id^=\"map_\"]');
        allMaps.forEach(function(map) {{
            map.style.display = 'none';
        }});
        var selectedMap = document.getElementById('map_' + radius);
        if (selectedMap) {{
            selectedMap.style.display = 'block';
        }}
    }}
    document.addEventListener('DOMContentLoaded', function() {{
        updateMap(parseFloat({radius_range[0]}).toFixed(1));  // Display the initial map
    }});
    </script>
    <input type="range" min="{radius_range[0]}" max="{radius_range[1]}" step="{step}" onchange="updateMap(this.value)" />
    """

    # Combine all maps and slider into a single HTML file
    full_html = f"<html><head></head><body>{slider_control_js}{maps_html}</body></html>"
    with open("optimal_point_map.html", "w") as f:
        f.write(full_html)

def main():
    parser = argparse.ArgumentParser(description="Find the optimal point within a bounding circle that is furthest from a set of coordinates and within the radius.")
    parser.add_argument("file_path", type=str, help="Path to the CSV file containing coordinates.")
    parser.add_argument("--radius_range", type=float, nargs=2, default=[11, 17], help="Range of radii to consider in kilometers (default: 11 to 17 km).")
    parser.add_argument("--step", type=float, default=0.5, help="Step size for radius in kilometers (default: 0.5 km).")
    parser.add_argument("--center_lat", type=float, default=40.050250, help="Latitude of the center point (default: 40.014984).")
    parser.add_argument("--center_lon", type=float, default=-105.247580, help="Longitude of the center point (default: -105.2797).")
    args = parser.parse_args()

    # Read coordinates from file
    points = read_coordinates_from_file(args.file_path)

    # Set radius range, step, and center point
    radius_range = args.radius_range
    step = args.step
    center = (args.center_lat, args.center_lon)

    # Precompute optimal points for the range of radii
    optimal_points = precompute_optimal_points(points, center, radius_range, step)

    # Plot the maps for each radius with slider control to select radius
    plot_maps(points, optimal_points, center, radius_range, step)
    print("Map saved as 'optimal_point_map.html'")
    print("CSV file saved as 'optimal_points.csv'")

if __name__ == "__main__":
    main()
