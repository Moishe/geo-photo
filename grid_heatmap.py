import argparse
import folium
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, Polygon
from math import sqrt, radians, cos
import matplotlib.pyplot as plt

# Load boundary shapefile based on area type
def load_boundary_shapefile(area_type):
    if area_type == "state":
        return gpd.read_file("shapefiles/tl_2024_us_state.shp")
    elif area_type == "county":
        return gpd.read_file("shapefiles/tl_2024_us_county.shp")
    elif area_type == "city":
        return gpd.read_file("shapefiles/tl_2024_us_place.shp")
    else:
        raise ValueError("Unsupported geographical type")

# Get the bounding box for a specified area
def get_bounding_box(geo_area):
    area_type, area_name = geo_area.split(":")
    gdf = load_boundary_shapefile(area_type)
    
    # Filter GeoDataFrame based on area name and type
    if area_type == "state":
        filtered_gdf = gdf[gdf['NAME'].str.contains(area_name, case=False)]
    elif area_type == "county":
        filtered_gdf = gdf[gdf['NAMELSAD'].str.contains(area_name, case=False)]
    elif area_type == "city":
        filtered_gdf = gdf[gdf['NAME'].str.contains(area_name, case=False)]
    
    if filtered_gdf.empty:
        raise ValueError(f"No matching boundary found for {geo_area}")
    
    # Get the bounding box of the area
    bounding_box = filtered_gdf.total_bounds
    return bounding_box, filtered_gdf.geometry.unary_union

# Helper function to create a grid over a bounding box
def create_grid(bbox, grid_size_meters):
    minx, miny, maxx, maxy = bbox
    grid_cells = []
    
    # Convert grid size in meters to degrees
    grid_size_degrees = grid_size_meters / 111320  # Approximate conversion

    x_coords = np.arange(minx, maxx, grid_size_degrees)
    y_coords = np.arange(miny, maxy, grid_size_degrees)
    
    for x in x_coords:
        for y in y_coords:
            cell = Polygon([(x, y), (x + grid_size_degrees, y), 
                            (x + grid_size_degrees, y + grid_size_degrees), (x, y + grid_size_degrees)])
            grid_cells.append(cell)
    
    return gpd.GeoDataFrame(grid_cells, columns=['geometry'], crs="EPSG:4326")

# Function to calculate the influence score for each grid cell
def calculate_influence(grid, points, influence_radius_meters):
    influence_radius_degrees = influence_radius_meters / 111320  # Rough conversion
    
    # Add a column to store influence scores
    grid['influence_score'] = 0.0
    
    for _, point in points.iterrows():
        point_geom = point.geometry
        for i, cell in grid.iterrows():
            cell_center = cell.geometry.centroid
            distance = point_geom.distance(cell_center)
            
            if distance <= influence_radius_degrees:
                grid.at[i, 'influence_score'] += 1 / max(distance, 1e-6)  # Prevent division by zero
    
    return grid

# Main function to create heatmap
def create_heatmap(geo_area, grid_size, influence_radius, csv_file):
    bounding_box, boundary_shape = get_bounding_box(geo_area)
    
    # Read points from CSV
    points_df = pd.read_csv(csv_file)
    points_df['geometry'] = points_df.apply(lambda row: Point(row['longitude'], row['latitude']), axis=1)
    points_gdf = gpd.GeoDataFrame(points_df, geometry='geometry', crs="EPSG:4326")
    
    # Clip points to bounding shape
    points_gdf = points_gdf[points_gdf.geometry.within(boundary_shape)]
    
    # Define grid based on bounding box and calculate influence
    grid = create_grid(bounding_box, grid_size)
    grid = calculate_influence(grid, points_gdf, influence_radius)
    
    # Find cell with lowest influence and create map
    lowest_score_cell = grid.loc[grid['influence_score'].idxmin()]
    lowest_cell_center = lowest_score_cell.geometry.centroid
    lowest_cell_coords = (lowest_cell_center.y, lowest_cell_center.x)
    
    # Initialize map
    m = folium.Map(location=lowest_cell_coords, zoom_start=10)
    
    # Normalize influence scores for coloring
    max_influence = grid['influence_score'].max()
    min_influence = grid['influence_score'].min()
    
    # Add grid cells as colored polygons based on influence score
    for _, cell in grid.iterrows():
        normalized_score = (cell['influence_score'] - min_influence) / (max_influence - min_influence)
        color = plt.cm.RdYlBu(1 - normalized_score)  # 1 - normalized_score for red (high) to blue (low)
        color_hex = f"#{int(color[0]*255):02x}{int(color[1]*255):02x}{int(color[2]*255):02x}"
        
        folium.GeoJson(
            cell.geometry,
            style_function=lambda x, color=color_hex: {'color': color, 'fillOpacity': 0.5}
        ).add_to(m)
    
    # Add links to Google Maps and Gaia GPS for the lowest influence cell
    folium.Marker(
        location=lowest_cell_coords,
        popup=(f"<a href='https://www.google.com/maps/search/?api=1&query={lowest_cell_coords[0]},{lowest_cell_coords[1]}' target='_blank'>Google Maps Link</a><br>"
               f"<a href='https://www.gaiagps.com/map/?lat={lowest_cell_coords[0]}&lon={lowest_cell_coords[1]}' target='_blank'>Gaia GPS Link</a>"),
        icon=folium.Icon(color="blue")
    ).add_to(m)
    
    # Save map to HTML
    output_html = 'heatmap.html'
    m.save(output_html)
    print(f"Map saved to {output_html}")

# Argument parsing
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a heatmap from geographical data points.")
    parser.add_argument("--geo_area", type=str, required=True, help="Geographical area (e.g., 'city:Boulder', 'county:Boulder', 'state:Colorado')")
    parser.add_argument("--grid_size", type=int, required=True, help="Grid size in meters")
    parser.add_argument("--influence_radius", type=int, required=True, help="Influence radius in meters")
    parser.add_argument("--csv_file", type=str, required=True, help="Path to CSV file with latitude and longitude data")
    
    args = parser.parse_args()
    
    create_heatmap(args.geo_area, args.grid_size, args.influence_radius, args.csv_file)
