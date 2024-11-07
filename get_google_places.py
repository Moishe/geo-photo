import os
import requests
import csv
import time

def get_places_with_photos(location, radius=2000, max_results=10000):
    # Get the API key from environment variables
    api_key = os.environ.get('PERSONAL_GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("Please set the PERSONAL_GOOGLE_API_KEY environment variable.")
    
    # Define the endpoint URL
    endpoint_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    
    # Define the parameters
    params = {
        'location': location,  # Location string in the form "lat,long"
        'radius': radius,      # Search radius in meters
        'type': 'point_of_interest',  # Exclude businesses by focusing on points of interest
        'key': api_key         # Your API key
    }
    
    places_with_photos = []
    next_page_token = None

    while len(places_with_photos) < max_results:
        if next_page_token:
            params['pagetoken'] = next_page_token
            # Wait to avoid INVALID_REQUEST due to next_page_token not being ready
            time.sleep(2)

        # Make a request to the Google Maps API
        response = requests.get(endpoint_url, params=params)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Parse the response JSON
            response_json = response.json()
            places = response_json.get('results', [])
            print(response_json.get('status'), response_json.get('next_page_token') is not None, len(response_json.get('results')))
            
            # Extract places that have photos
            places_with_photos.extend([
                {'lat': place['geometry']['location']['lat'], 'lng': place['geometry']['location']['lng']}
                for place in places if 'photos' in place
            ])
            
            # Check for next page token
            next_page_token = response_json.get('next_page_token')
            if not next_page_token:
                break
        else:
            print("Failed to fetch data:", response.status_code)
            break

    return places_with_photos[:max_results]

def create_grid(center_lat, center_lng, grid_size_km, radius_km):
    grid_points = []
    lat_step = grid_size_km / 110.574  # Approximate km per degree latitude
    lng_step = grid_size_km / (111.320 * abs(center_lat))  # Approximate km per degree longitude, varies with latitude

    for lat_offset in range(-radius_km // grid_size_km, radius_km // grid_size_km + 1):
        for lng_offset in range(-radius_km // grid_size_km, radius_km // grid_size_km + 1):
            grid_lat = center_lat + (lat_offset * lat_step)
            grid_lng = center_lng + (lng_offset * lng_step)
            grid_points.append(f"{grid_lat},{grid_lng}")

    return grid_points

# Example usage
if __name__ == "__main__":
    # Location for Boulder, CO
    center_lat = 40.0150
    center_lng = -105.2705
    radius_km = 20
    grid_size_km = 2

    # Create grid of locations
    grid_locations = create_grid(center_lat, center_lng, grid_size_km, radius_km)
    all_places_with_photos = []

    # Fetch places with photos for each location in the grid
    for location in grid_locations:
        try:
            places = get_places_with_photos(location, radius=2000)
            all_places_with_photos.extend(places)
            time.sleep(2)  # To avoid rate limiting
        except ValueError as e:
            print(e)

    # Remove duplicates
    unique_places = {f"{place['lat']},{place['lng']}": place for place in all_places_with_photos}.values()
    
    # Write results to a CSV file
    with open('places_with_photos.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Latitude', 'Longitude'])
        for place in unique_places:
            writer.writerow([place['lat'], place['lng']])