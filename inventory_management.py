import pandas as pd
from datetime import datetime
import s3fs
import streamlit as st

def get_s3_fs():
    return s3fs.S3FileSystem(
        key=st.secrets["aws"]["AWS_ACCESS_KEY_ID"],
        secret=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"],
        client_kwargs={
            'region_name': st.secrets["aws"]["AWS_DEFAULT_REGION"]
        }
    )

def update_box_inventory(box_type, new_quantity, update_date=None):
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    filename = "box_inventory.csv"
    full_path = f"{bucket_name}/{filename}"
    
    if update_date is None:
        update_date = datetime.now().date()
    else:
        update_date = pd.to_datetime(update_date).date()
    
    if s3.exists(full_path):
        with s3.open(full_path, 'r') as f:
            inventory = pd.read_csv(f)
    else:
        inventory = pd.DataFrame(columns=['box_type', 'quantity', 'last_updated'])
    
    if box_type in inventory['box_type'].values:
        inventory.loc[inventory['box_type'] == box_type, 'quantity'] = new_quantity
        inventory.loc[inventory['box_type'] == box_type, 'last_updated'] = update_date
    else:
        new_row = pd.DataFrame({'box_type': [box_type], 'quantity': [new_quantity], 'last_updated': [update_date]})
        inventory = pd.concat([inventory, new_row], ignore_index=True)
    
    with s3.open(full_path, 'w') as f:
        inventory.to_csv(f, index=False, date_format='%Y-%m-%d')

def get_box_inventory():
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    filename = "box_inventory.csv"
    full_path = f"{bucket_name}/{filename}"
    
    if s3.exists(full_path):
        with s3.open(full_path, 'r') as f:
            inventory = pd.read_csv(f)
        # Remove duplicates if any, keeping the last occurrence
        inventory = inventory.drop_duplicates(subset='box_type', keep='last')
        # Ensure all necessary columns exist
        for col in ['quantity', 'last_updated']:
            if col not in inventory.columns:
                inventory[col] = 0 if col == 'quantity' else pd.NaT
        # Convert to dictionary with box_type as key and a dict of quantity and last_updated as value
        return inventory.set_index('box_type').to_dict(orient='index')
    else:
        return {}

def initialize_inventory_if_empty():
    inventory = get_box_inventory()
    if not inventory:
        initial_inventory = {
            '3001': 1000,
            '3002': 1000,
            '3003': 1000,
            '3004': 1000,
            '3005': 1000,
            '3006': 1000,
            '3008': 1000
        }
        current_date = datetime.now().date()
        for box_type, quantity in initial_inventory.items():
            update_box_inventory(box_type, quantity, current_date)

def adjust_inventory_for_usage():
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    inventory_file = "box_inventory.csv"
    usage_file = "daily_box_usage.csv"
    inventory_path = f"{bucket_name}/{inventory_file}"
    usage_path = f"{bucket_name}/{usage_file}"
    
    if not s3.exists(inventory_path) or not s3.exists(usage_path):
        return  # Wenn eine der Dateien nicht existiert, beenden wir die Funktion
    
    with s3.open(inventory_path, 'r') as f:
        inventory = pd.read_csv(f)
    
    with s3.open(usage_path, 'r') as f:
        usage = pd.read_csv(f)
    
    if 'last_updated' not in inventory.columns:
        inventory['last_updated'] = pd.NaT
    
    inventory['last_updated'] = pd.to_datetime(inventory['last_updated']).dt.date
    usage['date'] = pd.to_datetime(usage['date']).dt.date
    
    for _, inv_row in inventory.iterrows():
        box_type = inv_row['box_type']
        last_updated = inv_row['last_updated']
        
        if pd.isnull(last_updated):
            continue
        
        recent_usage = usage[(usage['box_type'] == box_type) & (usage['date'] > last_updated)]
        total_usage = recent_usage['quantity'].sum()
        
        inventory.loc[inventory['box_type'] == box_type, 'quantity'] -= total_usage
        inventory.loc[inventory['box_type'] == box_type, 'last_updated'] = datetime.now().date()
    
    # Ensure quantity never goes below zero
    inventory['quantity'] = inventory['quantity'].clip(lower=0)
    
    # Remove duplicates if any, keeping the last occurrence
    inventory = inventory.drop_duplicates(subset='box_type', keep='last')
    
    with s3.open(inventory_path, 'w') as f:
        inventory.to_csv(f, index=False)
