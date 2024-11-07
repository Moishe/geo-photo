import sqlite3
import csv
from pathlib import Path

def extract_geolocation_data(db_path):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query to select latitude and longitude from the ZASSET table
    query = """
    SELECT
        ZLATITUDE,
        ZLONGITUDE
    FROM
        ZASSET
    WHERE
        ZLATITUDE IS NOT NULL
        AND ZLONGITUDE IS NOT NULL;
    """

    try:
        cursor.execute(query)
        data = cursor.fetchall()
        return data
    finally:
        conn.close()

def write_to_csv(data, output_path):
    # Write the data to a CSV file
    with open(output_path, 'w', newline='') as file:
        writer = csv.writer(file)
        # Writing header
        writer.writerow(['latitude', 'longitude'])
        writer.writerows(data)

def main():
    # Path to the database within the Photos Library
    photos_db_path = Path.home() / 'Pictures/Photos Library.photoslibrary/database/Photos.sqlite'
    output_csv_path = Path.home() / 'Desktop/photo_geolocations.csv'
    
    # Check if the database file exists
    if not photos_db_path.exists():
        print("Photos database does not exist at the expected location.")
        return

    # Extract data
    geolocation_data = extract_geolocation_data(str(photos_db_path))
    
    if geolocation_data:
        # Write data to CSV
        write_to_csv(geolocation_data, str(output_csv_path))
        print(f"Data successfully written to {output_csv_path}")
    else:
        print("No geolocation data found.")

if __name__ == '__main__':
    main()
