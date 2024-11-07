from collections import defaultdict
import os
import numpy as np
import requests
import csv

def fetch_all_photos(api_key, latitude, longitude, radius=30):
    # Base URL for the Flickr API
    base_url = "https://api.flickr.com/services/rest/"

    photos_by_owner = defaultdict(list)
    photos_by_id = {}

    page = 1
    with open('photo_coordinates_for_sample.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['latitude', 'longitude'])

        while True:
            # Parameters for the API call
            params = {
                'method': 'flickr.photos.search',
                'api_key': api_key,
                'format': 'json',
                'nojsoncallback': 1,
                'has_geo': 1,  # ensure photos have geolocation data
                'lat': latitude,  # latitude of the center point
                'lon': longitude,  # longitude of the center point
                'radius': radius,  # radius in kilometers
                'content_type': 1,  # photos only
                'radius_units': 'km',
                'accuracy': 16,  # level of accuracy corresponds to city/zip code
                'extras': 'geo',  # request geolocation data
                'per_page': 250,  # number of photos per page
                'page': page  # page number
            }

            # Fetch the data from Flickr API
            response = requests.get(base_url, params=params)
            data = response.json()

            # Check if the response contains photos and if we are on a valid page
            if data and 'photos' in data and 'photo' in data['photos'] and data['photos']['photo']:
                photos = data['photos']['photo']
                # Write photo coordinates to the CSV file
                for photo in photos:
                    photos_by_owner[photo['owner']].append(photo)
                    photos_by_id[photo['id']] = photo
                    writer.writerow([photo['id'], photo['owner'], photo['title'], photo['woeid'], photo['accuracy'], photo['latitude'], photo['longitude']])

                total_pages = data['photos']['pages']
                print(f"{page} / {total_pages}")
                if page >= total_pages:
                    break  # Break the loop if we're on the last page
                page += 1  # Increment page number to fetch next page
            else:
                print("No more photos found or error in fetching data.")
                break

    print("CSV file has been written with all photo coordinates.")
    print("Writing sampled file")

    with open('photo_coordinates_owner_sampled.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['latitude', 'longitude'])

        for owner, photos in photos_by_owner.items():
            photo = np.random.choice(photos)
            writer.writerow([photo['latitude'], photo['longitude']])

    with open('photo_coordinates_id_deduped.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['latitude', 'longitude'])

        for id, photo in photos_by_id.items():
            writer.writerow([photo['latitude'], photo['longitude']])

api_key = os.getenv("FLICKR_API_KEY")
latitude = 40.014984  # example latitude
longitude = -105.2797  # example longitude
#latitude = 40.097505
#longitude = -105.301871

fetch_all_photos(api_key, latitude, longitude)
