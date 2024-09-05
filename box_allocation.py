def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def allocate_box(order):
    order_items = [item for item in order.get('OrderItems', []) if item.get('Product') is not None]
    total_items = sum(safe_float(item.get('Quantity', 0)) for item in order_items)
    total_weight = sum(
        safe_float(item.get('Product', {}).get('Weight', 0)) * safe_float(item.get('Quantity', 0))
        for item in order_items
    )
    special_skus = ['8000', '8001', '8002', '8003', '8004']

    # Check for special SKUs
    special_sku_items = [
        item for item in order_items 
        if item.get('Product', {}).get('SKU') in special_skus
    ]
    
    if len(special_sku_items) == len(order_items) and len(special_sku_items) == 1:
        return '3001', f"Single special SKU: {special_sku_items[0].get('Product', {}).get('SKU')}"

    # Check for specific SKU quantities
    sku_80510_count = sum(safe_float(item.get('Quantity', 0)) for item in order_items if item.get('Product', {}).get('SKU') == '80510')
    sku_80511_count = sum(safe_float(item.get('Quantity', 0)) for item in order_items if item.get('Product', {}).get('SKU') == '80511')

    if sku_80510_count == 1 or sku_80511_count == 1:
        return '3005', f"1x SKU 80510/80511"
    elif sku_80510_count == 2:
        return '3006', "2x SKU 80510"
    elif sku_80510_count == 3:
        return '3008', "3x SKU 80510"
    elif sku_80511_count == 2:
        return '3005', "2x SKU 80511"
    elif sku_80511_count == 3:
        return '3006', "3x SKU 80511"

    # Check total weight
    if 10 <= total_weight < 20:
        return '3006', f"Total weight: {total_weight:.2f} kg"
    elif 20 <= total_weight <= 30:
        return '3008', f"Total weight: {total_weight:.2f} kg"

    # Other allocation rules
    if total_items == 1:
        return '3001', "1 item"
    elif total_items == 2:
        return '3002', "2 items"
    elif 3 <= total_items <= 4:
        return '3003', f"{total_items} items"
    elif any(item.get('Product', {}).get('SKU') == '80533' for item in order_items):
        return '3004', "Contains SKU 80533"
    elif (5 <= total_items <= 10 and total_weight <= 10) or \
         (sku_80510_count == 1) or \
         (sku_80511_count == 1):
        return '3005', f"{total_items} items, weight: {total_weight:.2f} kg"

    # If no allocation is possible
    return None, "No allocation rule matched"
