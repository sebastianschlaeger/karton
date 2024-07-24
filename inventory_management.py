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

def update_box_inventory(box_type, quantity_change):
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    filename = "box_inventory.csv"
    full_path = f"{bucket_name}/{filename}"
    
    if s3.exists(full_path):
        with s3.open(full_path, 'r') as f:
            inventory = pd.read_csv(f)
    else:
        inventory = pd.DataFrame(columns=['box_type', 'quantity', 'last_updated'])
    
    current_date = datetime.now().date()
    
    if box_type in inventory['box_type'].values:
        inventory.loc[inventory['box_type'] == box_type, 'quantity'] += quantity_change
        inventory.loc[inventory['box_type'] == box_type, 'last_updated'] = current_date
    else:
        new_row = pd.DataFrame({'box_type': [box_type], 'quantity': [quantity_change], 'last_updated': [current_date]})
        inventory = pd.concat([inventory, new_row], ignore_index=True)
    
    # Ensure quantity never goes below zero
    inventory['quantity'] = inventory['quantity'].clip(lower=0)
    
    with s3.open(full_path, 'w') as f:
        inventory.to_csv(f, index=False)

def get_box_inventory():
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    filename = "box_inventory.csv"
    full_path = f"{bucket_name}/{filename}"
    
    if s3.exists(full_path):
        with s3.open(full_path, 'r') as f:
            inventory = pd.read_csv(f)
        return inventory.set_index('box_type').to_dict(orient='index')
    else:
        return {}

def set_initial_inventory(initial_inventory):
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    filename = "box_inventory.csv"
    full_path = f"{bucket_name}/{filename}"
    
    inventory = pd.DataFrame(list(initial_inventory.items()), columns=['box_type', 'quantity'])
    
    with s3.open(full_path, 'w') as f:
        inventory.to_csv(f, index=False)

# Initialize inventory if it doesn't exist
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
        set_initial_inventory(initial_inventory)
