import json
import time
import csv
import os
import pandas as pd
import joblib
from datetime import datetime

# Rutas de archivos
DATA_PATH = "/run/readsb/aircraft.json"
MODEL_PATH = "models/flight_anomaly_model.pkl"
CSV_PREDICTIONS = "data/flight_data/live_predictions.csv"

print("📡 Booting up Edge AI Inference System...")

# 1. Cargamos el modelo de IA con Try-Except
try:
    model = joblib.load(MODEL_PATH)
    print(f"✅ AI Model loaded successfully from {MODEL_PATH}")
except FileNotFoundError as e:
    print(f"❌ CRITICAL ERROR: AI Model not found at {MODEL_PATH}.")
    print("Please upload the .pkl file from Google Colab.")
    print(e)
    exit() # Detenemos el programa si no hay cerebro

# 2. Preparamos el nuevo archivo CSV
file_exists = os.path.isfile(CSV_PREDICTIONS)
with open(CSV_PREDICTIONS, mode='a', newline='') as file:
    writer = csv.writer(file)
    if not file_exists:
        # Añadimos las dos variables nuevas: Status y Anomaly_Score
        writer.writerow(["Timestamp", "Flight", "Altitude_ft", "Speed_kt", "Latitude", "Longitude", "Status", "Anomaly_Score"])

print(f"📁 Saving AI predictions to: {CSV_PREDICTIONS}\n")
print("--- RADAR ACTIVE ---")

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
                
                # 3. PREPARAR DATOS PARA LA IA
                # Scikit-learn necesita que los datos se llamen igual que en el entrenamiento
                input_data = pd.DataFrame(
                    [[alt, speed, lat, lon]], 
                    columns=['Altitude_ft', 'Speed_kt', 'Latitude', 'Longitude']
                )
                
                # 4. PREDICCIÓN EN TIEMPO REAL
                prediction = model.predict(input_data)[0] # 1 Normal, -1 Anomalía
                score = model.decision_function(input_data)[0] # Puntaje matemático
                
                # 5. LÓGICA DE ALERTAS
                if prediction == 1:
                    status = "NORMAL"
                    print(f"[{timestamp}] 🟢 {flight} | Alt: {alt} ft | Spd: {speed} kt | Status: {status}")
                else:
                    status = "ANOMALY"
                    # Si es anomalía, lo imprimimos con advertencias visuales
                    print(f"[{timestamp}]  WARNING! {flight} behaves abnormally! | Score: {score:.3f}")
                
                # 6. GUARDAR EN EL NUEVO DATASET
                with open(CSV_PREDICTIONS, mode='a', newline='') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow([timestamp, flight, alt, speed, lat, lon, status, round(score, 3)])
                
    except FileNotFoundError:
        print("Waiting for SDR data...")
    
    time.sleep(2)