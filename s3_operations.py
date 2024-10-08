import pandas as pd
from datetime import datetime, timedelta, date
import s3fs
import streamlit as st
import traceback

def get_s3_fs():
    return s3fs.S3FileSystem(
        key=st.secrets["aws"]["AWS_ACCESS_KEY_ID"],
        secret=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"],
        client_kwargs={
            'region_name': st.secrets["aws"]["AWS_DEFAULT_REGION"]
        }
    )

def get_summary_data():
    try:
        s3 = get_s3_fs()
        bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
        inventory_file = "box_inventory.csv"
        usage_file = "daily_box_usage.csv"
        inventory_path = f"{bucket_name}/{inventory_file}"
        usage_path = f"{bucket_name}/{usage_file}"
        
        if not (s3.exists(inventory_path) and s3.exists(usage_path)):
            st.warning("Inventar- oder Nutzungsdatei nicht gefunden.")
            return pd.DataFrame()
        
        with s3.open(inventory_path, 'r') as f:
            inventory = pd.read_csv(f)
        
        with s3.open(usage_path, 'r') as f:
            usage = pd.read_csv(f)
        
        # Überprüfen und ggf. umbenennen der Spalten
        required_inventory_columns = ['box_type', 'quantity', 'last_updated']
        required_usage_columns = ['box_type', 'quantity', 'date']
        
        if not all(col in inventory.columns for col in required_inventory_columns):
            st.error("Erforderliche Spalten nicht in der Inventardatei gefunden.")
            return pd.DataFrame()
        
        if not all(col in usage.columns for col in required_usage_columns):
            st.error("Erforderliche Spalten nicht in der Nutzungsdatei gefunden.")
            return pd.DataFrame()
        
        # Konvertiere Datumsspalten
        inventory['last_updated'] = pd.to_datetime(inventory['last_updated']).dt.date
        usage['date'] = pd.to_datetime(usage['date']).dt.date
        
        # Definiere ein Dictionary für die Produktnamen
        product_names = {
            '3001': 'Karton 1er',
            '3002': 'Karton 2er',
            '3003': 'Karton 4er',
            '3004': '25er Würfel (214)',
            '3005': 'Karton 10 kg',
            '3006': 'Karton 20 kg',
            '3008': 'Karton 30 kg'
        }

        summary = []
        for _, row in inventory.iterrows():
            box_type = row['box_type']
            box_type_str = str(box_type)  # Separate string version for product name lookup
            original_quantity = row['quantity']
            last_updated = row['last_updated']
            
            # Berechne den Verbrauch seit dem letzten Aktualisierungsdatum
            recent_usage = usage[(usage['box_type'] == box_type) & (usage['date'] > last_updated)]
            usage_since_update = recent_usage['quantity'].sum()
            
            # Berechne den aktuellen Bestand
            current_quantity = max(0, original_quantity - usage_since_update)
            
            # Berechne den Verbrauch der letzten 30 Tage
            today = datetime.now().date()
            thirty_days_ago = today - timedelta(days=30)
            usage_last_30_days = usage[(usage['box_type'] == box_type) & (usage['date'] >= thirty_days_ago)]['quantity'].sum()
            
            # Berechne die Bestandsreichweite in Tagen
            days_left = current_quantity / (usage_last_30_days / 30) if usage_last_30_days > 0 else float('inf')
            
            summary.append({
                'Kartontyp': box_type,
                'Produktname': product_names.get(box_type_str, f'Unbekannt ({box_type_str})'),
                'Ursprünglicher Bestand': int(original_quantity),
                'Verbrauch seit letzter Aktualisierung': int(usage_since_update),
                'Aktueller Bestand': int(current_quantity),
                'Verbrauch letzte 30 Tage': int(usage_last_30_days),
                'Reichweite (Tage)': f"{days_left:.1f}",
                'Zuletzt aktualisiert': last_updated
            })
        
        # Erstelle das DataFrame und sortiere es nach 'Kartontyp'
        df = pd.DataFrame(summary)
        df['Kartontyp'] = pd.to_numeric(df['Kartontyp'], errors='coerce')
        df = df.sort_values('Kartontyp')
        
        return df
    except Exception as e:
        st.error(f"Fehler bei der Verarbeitung der Daten: {str(e)}")
        st.error(f"Stacktrace: {traceback.format_exc()}")
        return pd.DataFrame()

def clear_order_data():
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    daily_usage_file = "daily_box_usage.csv"
    
    file_path = f"{bucket_name}/{daily_usage_file}"
    if s3.exists(file_path):
        s3.rm(file_path)

def get_daily_usage(date):
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    filename = "daily_box_usage.csv"
    full_path = f"{bucket_name}/{filename}"
    
    if s3.exists(full_path):
        with s3.open(full_path, 'r') as f:
            usage = pd.read_csv(f)
        usage['date'] = pd.to_datetime(usage['date']).dt.date
        return usage[usage['date'] == date]
    return pd.DataFrame()

def update_box_usage(box_type, quantity, process_date):
    if not isinstance(process_date, date):
        raise ValueError(f"Ungültiges Datumsformat: {process_date}")
    
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
    date_str = process_date.isoformat()
    
    # Überprüfen, ob für diesen Tag bereits ein Eintrag existiert
    mask = (usage['date'] == date_str) & (usage['box_type'] == box_type)
    if mask.any():
        # Ersetze den bestehenden Eintrag
        usage.loc[mask, 'quantity'] = quantity
    else:
        # Füge einen neuen Eintrag hinzu
        new_row = pd.DataFrame({'date': [date_str], 'box_type': [box_type], 'quantity': [quantity]})
        usage = pd.concat([usage, new_row], ignore_index=True)
    
    # Sortiere das DataFrame nach Datum in absteigender Reihenfolge
    usage['date'] = pd.to_datetime(usage['date'])
    usage = usage.sort_values('date', ascending=False)
    
    with s3.open(full_path, 'w') as f:
        usage.to_csv(f, index=False, date_format='%Y-%m-%d')
