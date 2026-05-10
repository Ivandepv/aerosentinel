import joblib
import pandas as pd

MODEL_PATH = "models/flight_anomaly_model.pkl"

print("Starting model stress test...")

try:
    model = joblib.load(MODEL_PATH)
    
    # Injecting fake data (Severe nosedive: Low alt, High speed)
    # Injecting EXTREME fake data (Sensor Glitch Simulation)
    # Alt: -10000 ft (Underground) | Speed: 5000 kt (Hypersonic) | Lat/Lon: 0,0 (Equator)
    fake_data = pd.DataFrame(
        [[-10000, 5000, 0.0, 0.0]], 
        columns=['Altitude_ft', 'Speed_kt', 'Latitude', 'Longitude']
    )
    
    print("\n✈️ Injecting Ghost Flight: GHOST-02 | Alt: -10000 ft | Spd: 5000 kt")
    
    prediction = model.predict(fake_data)[0]
    score = model.decision_function(fake_data)[0]
    
    if prediction == -1:
        print(f"🔴 SUCCESS! Anomaly detected. Score: {score:.3f}")
    else:
        print("🟢 Test failed. Model evaluated this as normal.")
        
except FileNotFoundError:
    print("Model not found. Check the file path.")