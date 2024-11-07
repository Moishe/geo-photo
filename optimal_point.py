import numpy as np
from scipy.optimize import minimize
import folium
import argparse
import csv

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

# Objective function to maximize the minimum distance to any point in the set
def objective_function(x, points, center, radius):
    distances = [haversine(x, p) for p in points]
    # Apply penalty if point is outside the bounding circle
    if haversine(x, center) > radius:
        return 0  # Clamp distance to 0 if outside the bounding radius
    return -min(distances)  # negative because we need to maximize

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
    for radius in np.arange(radius_range[0], radius_range[1] + step, step):
        radius = round(radius, 2)  # Round radius to avoid floating point issues with IDs
        initial_guess = center
        bounds = [(center[0] - 10, center[0] + 10), (center[1] - 10, center[1] + 10)]
        result = minimize(objective_function, initial_guess, args=(points, center, radius),
                          method='L-BFGS-B', bounds=bounds, options={'maxiter': 10000, 'ftol': 1e-6})
        if result.success:
            optimal_points[radius] = result.x
        else:
            print(f"Optimization failed for radius {radius} km: {result.message}")
    return optimal_points

def plot_maps(points, optimal_points, center, radius_range, step):
    maps_html = ""
    for radius, optimal_point in optimal_points.items():
        # Create a map centered around the average of the points
        avg_lat = np.mean([p[0] for p in points])
        avg_lon = np.mean([p[1] for p in points])
        folium_map = folium.Map(location=[avg_lat, avg_lon], zoom_start=10)

        # Plot all points as dark green dots
        for point in points:
            folium.CircleMarker(location=point, radius=1, color='darkgreen', fill=True, fill_color='darkgreen').add_to(folium_map)

        # Plot the optimal point as a red dot
        folium.CircleMarker(location=optimal_point, radius=5, color='red', fill=True, fill_color='red').add_to(folium_map)

        # Plot the bounding circle
        folium.Circle(location=center, radius=radius * 1000, color='green', fill=False).add_to(folium_map)

        # Save the map HTML to a string
        map_html = folium_map._repr_html_()
        lat, lon = optimal_point
        google_maps_link = f"https://www.google.com/maps?q={lat},{lon}"
        maps_html += f'<div id="map_{radius:.1f}" style="display:none">{map_html}<br><p>Optimal Point Coordinates: {lat:.6f}, {lon:.6f} - <a href="{google_maps_link}" target="_blank">View on Google Maps</a> - <a href="https://www.gaiagps.com/map/?lat={lat}&lon={lon}&zoom=15" target="_blank">View on GaiaGPS</a></p></div>'

    # Add JavaScript to control visibility
    slider_control_js = f"""
    <script>
    function updateMap(radius) {{
        radius = parseFloat(radius).toFixed(2);  // Ensure radius matches the ID format
        var allMaps = document.querySelectorAll('[id^="map_"]');
        allMaps.forEach(function(map) {{
            map.style.display = 'none';
        }});
        var selectedMap = document.getElementById('map_' + parseFloat(radius).toFixed(1));
        if (selectedMap) {{
            selectedMap.style.display = 'block';
        }}
    }}
    document.addEventListener('DOMContentLoaded', function() {{
        updateMap(parseFloat({radius_range[0]}).toFixed(2));  // Display the initial map
    }});
    </script>
    <input type="range" min="{radius_range[0]}" max="{radius_range[1]}" step="{step}" onchange="updateMap(this.value)" />
    """

    # Combine all maps and slider into a single HTML file
    full_html = f"<html><head></head><body>{slider_control_js}{maps_html}</body></html>"
    with open("optimal_point_map.html", "w") as f:
        f.write(full_html)

def main():
    parser = argparse.ArgumentParser(description="Find the optimal point within a bounding circle that is furthest from a set of coordinates.")
    parser.add_argument("file_path", type=str, help="Path to the CSV file containing coordinates.")
    parser.add_argument("--radius_range", type=float, nargs=2, default=[11, 17], help="Range of radii to consider in kilometers (default: 11 to 17 km).")
    parser.add_argument("--step", type=float, default=0.5, help="Step size for radius in kilometers (default: 0.5 km).")
    parser.add_argument("--center_lat", type=float, default=40.014984, help="Latitude of the center point (default: 40.014984).")
    parser.add_argument("--center_lon", type=float, default=-105.2797, help="Longitude of the center point (default: -105.2797).")
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

if __name__ == "__main__":
    main()
