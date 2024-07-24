import pandas as pd
from s3_utils import get_s3_fs

def update_box_inventory(box_type, quantity_change):
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    filename = "box_inventory.csv"
    full_path = f"{bucket_name}/{filename}"
    
    if s3.exists(full_path):
        with s3.open(full_path, 'r') as f:
            inventory = pd.read_csv(f)
    else:
        inventory = pd.DataFrame(columns=['box_type', 'quantity'])
    
    if box_type in inventory['box_type'].values:
        inventory.loc[inventory['box_type'] == box_type, 'quantity'] += quantity_change
    else:
        new_row = pd.DataFrame({'box_type': [box_type], 'quantity': [quantity_change]})
        inventory = pd.concat([inventory, new_row], ignore_index=True)
    
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
        return dict(zip(inventory['box_type'], inventory['quantity']))
    else:
        return {}
