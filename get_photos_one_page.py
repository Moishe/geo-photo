import json
import os
import requests
import csv

def fetch_photos(api_key, latitude, longitude, radius='1'):
    # Base URL for the Flickr API
    base_url = "https://api.flickr.com/services/rest/"
    
    # Parameters for the API call
    params = {
        'method': 'flickr.photos.search',
        'api_key': api_key,
        'format': 'json',
        'nojsoncallback': 1,
        'has_geo': 1,  # ensure photos have geolocation data
        'lat': latitude,  # latitude of the center point
        'lon': longitude,  # longitude of the center point
        'accuracy': 11,  # level of accuracy corresponds to city/zip code
        'content_type': 1,  # photos only
        'geo_context': 2,  # taken outdoors
        'radius': radius,  # radius in kilometers
        'radius_units': 'km',
        'extras': 'geo',  # request geolocation data
        'per_page': 250,  # number of photos per page
        'page': 1  # page number
    }
    
    # Fetch the data from Flickr API
    response = requests.get(base_url, params=params)
    data = response.json()
    print(json.dumps(data, indent=2))
    
    # Check if the response contains photos
    if data and 'photos' in data and 'photo' in data['photos']:
        photos = data['photos']['photo']
        
        # Write photo coordinates to a CSV file
        with open('photo_coordinates.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['latitude', 'longitude'])
            
            for photo in photos:
                writer.writerow([photo['latitude'], photo['longitude']])
                
        print("CSV file has been written with photo coordinates.")
    else:
        print("No photos found or error in fetching data.")

# Replace 'YOUR_API_KEY' with your actual Flickr API key
api_key = os.getenv("FLICKR_API_KEY")
print(f"using api key {api_key}")
latitude = 40.0176  # example latitude
longitude = -105.2797  # example longitude

fetch_photos(api_key, latitude, longitude)
