import pandas as pd
from datetime import datetime, timedelta, date
import s3fs
import streamlit as st
import json

def get_s3_fs():
    return s3fs.S3FileSystem(
        key=st.secrets["aws"]["AWS_ACCESS_KEY_ID"],
        secret=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"],
        client_kwargs={
            'region_name': st.secrets["aws"]["AWS_DEFAULT_REGION"]
        }
    )

def save_unallocated_orders(unallocated_orders):
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    filename = f"unallocated_orders_{datetime.now().strftime('%Y-%m-%d')}.json"
    full_path = f"{bucket_name}/{filename}"
    
    with s3.open(full_path, 'w') as f:
        json.dump(unallocated_orders, f)

def get_unallocated_orders():
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    today = datetime.now().date()
    filename = f"unallocated_orders_{today.strftime('%Y-%m-%d')}.json"
    full_path = f"{bucket_name}/{filename}"
    
    if s3.exists(full_path):
        with s3.open(full_path, 'r') as f:
            return json.load(f)
    else:
        return []
        
def get_summary_data():
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    inventory_file = "box_inventory.csv"
    usage_file = "daily_box_usage.csv"
    inventory_path = f"{bucket_name}/{inventory_file}"
    usage_path = f"{bucket_name}/{usage_file}"
    
    if not (s3.exists(inventory_path) and s3.exists(usage_path)):
        return pd.DataFrame()  # Leeres DataFrame zurückgeben
    
    try:
        with s3.open(inventory_path, 'r') as f:
            inventory = pd.read_csv(f)
        
        with s3.open(usage_path, 'r') as f:
            usage = pd.read_csv(f)
        
        # Überprüfen und ggf. umbenennen der Spalten
        if 'box_type' not in inventory.columns or 'quantity' not in inventory.columns:
            st.error("Erforderliche Spalten nicht in der Inventardatei gefunden.")
            return pd.DataFrame()
        
        if 'box_type' not in usage.columns or 'quantity' not in usage.columns or 'date' not in usage.columns:
            st.error("Erforderliche Spalten nicht in der Nutzungsdatei gefunden.")
            return pd.DataFrame()
        
        # Berechne den Verbrauch der letzten 30 Tage
        today = datetime.now().date()
        thirty_days_ago = today - timedelta(days=30)
        usage['date'] = pd.to_datetime(usage['date']).dt.date
        recent_usage = usage[usage['date'] >= thirty_days_ago]
        
        summary = []
        for _, row in inventory.iterrows():
            box_type = row['box_type']
            current_quantity = row['quantity']
            
            # Berechne den Verbrauch der letzten 30 Tage
            usage_last_30_days = recent_usage[recent_usage['box_type'] == box_type]['quantity'].sum()
            
            # Berechne den ursprünglichen Bestand
            original_quantity = current_quantity + usage_last_30_days
            
            # Berechne den durchschnittlichen täglichen Verbrauch
            daily_usage = usage_last_30_days / 30 if usage_last_30_days > 0 else 0  # Verhindere Division durch Null
            
            # Berechne die Bestandsreichweite in Tagen
            days_left = current_quantity / daily_usage if daily_usage > 0 else float('inf')
            
            summary.append({
                'Kartontyp': box_type,
                'Ursprünglicher Bestand': int(original_quantity),
                'Verbrauch (letzte 30 Tage)': int(usage_last_30_days),
                'Aktueller Bestand': int(current_quantity),
                'Reichweite (Tage)': f"{days_left:.1f}"
            })
        
        return pd.DataFrame(summary)
    except Exception as e:
        st.error(f"Fehler bei der Verarbeitung der Daten: {str(e)}")
        return pd.DataFrame()  # Im Fehlerfall leeres DataFrame zurückgeben

def clear_order_data():
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    daily_usage_file = "daily_box_usage.csv"
    unallocated_orders_file = f"unallocated_orders_{datetime.now().strftime('%Y-%m-%d')}.json"
    
    files_to_clear = [daily_usage_file, unallocated_orders_file]
    
    for file in files_to_clear:
        file_path = f"{bucket_name}/{file}"
        if s3.exists(file_path):
            s3.rm(file_path)

def update_box_usage(box_type, quantity, date):
    if not isinstance(date, datetime.date):
        raise ValueError(f"Ungültiges Datumsformat: {date}")
    
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    filename = "daily_box_usage.csv"
    full_path = f"{bucket_name}/{filename}"
    
    if s3.exists(full_path):
        with s3.open(full_path, 'r') as f:
            usage = pd.read_csv(f)
    else:
        usage = pd.DataFrame(columns=['date', 'box_type', 'quantity'])
    
    # Konvertiere das Datum in ein String-Format
    date_str = date.isoformat()
    
    # Überprüfen, ob für diesen Tag bereits ein Eintrag existiert
    mask = (usage['date'] == date_str) & (usage['box_type'] == box_type)
    if mask.any():
        # Aktualisiere den bestehenden Eintrag
        usage.loc[mask, 'quantity'] += quantity
    else:
        # Füge einen neuen Eintrag hinzu
        new_row = pd.DataFrame({'date': [date_str], 'box_type': [box_type], 'quantity': [quantity]})
        usage = pd.concat([usage, new_row], ignore_index=True)
    
    # Sortiere das DataFrame nach Datum in absteigender Reihenfolge
    usage['date'] = pd.to_datetime(usage['date'])
    usage = usage.sort_values('date', ascending=False)
    
    with s3.open(full_path, 'w') as f:
        usage.to_csv(f, index=False, date_format='%Y-%m-%d')
