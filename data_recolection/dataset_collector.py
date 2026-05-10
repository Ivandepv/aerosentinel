import json
import time
import csv
import os
from datetime import datetime

DATA_PATH = "/run/readsb/aircraft.json"
CSV_FILE = "data/training_data/flights_dataset.csv"


file_exists = os.path.isfile(CSV_FILE)


with open(CSV_FILE, mode='a', newline='') as file:
    writer = csv.writer(file)
  
    if not file_exists:
        writer.writerow(["Timestamp", "Flight", "Altitude_ft", "Speed_kt", "Latitude", "Longitude"])

print("📡 Starting ADS-B Data Logger for Edge AI...")
print(f"📁 Saving clean data to: {CSV_FILE}\n")

while True:
    try:
        with open(DATA_PATH, "r") as file:
            data = json.load(file)

        for aircraft in data.get("aircraft", []):
            flight = aircraft.get("flight", "").strip()
            alt = aircraft.get("alt_baro")
            speed = aircraft.get("gs")
            lat = aircraft.get("lat")
            lon = aircraft.get("lon")
            
            if flight and alt and speed and lat and lon:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                print(f"[{timestamp}] ✈️ {flight} | Alt: {alt} ft | Spd: {speed} kt | Pos: {lat}, {lon}")

                with open(CSV_FILE, mode='a', newline='') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow([timestamp, flight, alt, speed, lat, lon])
                
    except FileNotFoundError:
        print("Waiting for SDR data...")
    
    time.sleep(2)