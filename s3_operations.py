import pandas as pd
from datetime import datetime, timedelta
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
    usage_file = "box_usage.csv"
    inventory_path = f"{bucket_name}/{inventory_file}"
    usage_path = f"{bucket_name}/{usage_file}"
    
    if not (s3.exists(inventory_path) and s3.exists(usage_path)):
        return {}
    
    with s3.open(inventory_path, 'r') as f:
        inventory = pd.read_csv(f)
    
    with s3.open(usage_path, 'r') as f:
        usage = pd.read_csv(f)
    
    # Berechne den Verbrauch der letzten 30 Tage
    today = datetime.now().date()
    thirty_days_ago = today - timedelta(days=30)
    usage['date'] = pd.to_datetime(usage['date']).dt.date
    recent_usage = usage[usage['date'] >= thirty_days_ago]
    
    summary = {}
    for _, row in inventory.iterrows():
        box_type = row['box_type']
        current_quantity = row['quantity']
        
        # Berechne den ursprünglichen Bestand
        original_quantity = current_quantity + recent_usage[recent_usage['box_type'] == box_type]['quantity'].sum()
        
        # Berechne den Verbrauch der letzten 30 Tage
        usage_last_30_days = recent_usage[recent_usage['box_type'] == box_type]['quantity'].sum()
        
        # Berechne den durchschnittlichen täglichen Verbrauch
        daily_usage = usage_last_30_days / 30 if usage_last_30_days > 0 else 1  # Verhindere Division durch Null
        
        # Berechne die Bestandsreichweite in Tagen
        days_left = current_quantity / daily_usage if daily_usage > 0 else float('inf')
        
        summary[box_type] = {
            'original_quantity': original_quantity,
            'usage_last_30_days': usage_last_30_days,
            'current_quantity': current_quantity,
            'days_left': days_left
        }
    
    return summary

def clear_order_data():
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    usage_file = "box_usage.csv"
    daily_usage_file = "daily_box_usage.csv"
    unallocated_orders_file = f"unallocated_orders_{datetime.now().strftime('%Y-%m-%d')}.json"
    
    files_to_clear = [usage_file, daily_usage_file, unallocated_orders_file]
    
    for file in files_to_clear:
        file_path = f"{bucket_name}/{file}"
        if s3.exists(file_path):
            s3.rm(file_path)

def update_box_usage(box_type, quantity):
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    filename = "box_usage.csv"
    full_path = f"{bucket_name}/{filename}"
    today = datetime.now().date()
    
    if s3.exists(full_path):
        with s3.open(full_path, 'r') as f:
            usage = pd.read_csv(f)
    else:
        usage = pd.DataFrame(columns=['date', 'box_type', 'quantity'])
    
    new_row = pd.DataFrame({'date': [today], 'box_type': [box_type], 'quantity': [quantity]})
    usage = pd.concat([usage, new_row], ignore_index=True)
    
    with s3.open(full_path, 'w') as f:
        usage.to_csv(f, index=False)

def summarize_daily_usage():
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    usage_file = "box_usage.csv"
    summary_file = "daily_box_usage.csv"
    usage_path = f"{bucket_name}/{usage_file}"
    summary_path = f"{bucket_name}/{summary_file}"
    
    if not s3.exists(usage_path):
        return  # Wenn die Nutzungsdatei nicht existiert, beenden wir die Funktion
    
    with s3.open(usage_path, 'r') as f:
        usage = pd.read_csv(f)
    
    usage['date'] = pd.to_datetime(usage['date']).dt.date
    daily_summary = usage.groupby(['date', 'box_type'])['quantity'].sum().reset_index()
    
    with s3.open(summary_path, 'w') as f:
        daily_summary.to_csv(f, index=False)
