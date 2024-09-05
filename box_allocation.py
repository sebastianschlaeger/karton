def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def allocate_box(order_items):
    total_items = sum(safe_float(item.get('Quantity', 0)) for item in order_items)
    total_weight = sum(safe_float(item.get('Product', {}).get('WeightInGram', 0)) * safe_float(item.get('Quantity', 0)) for item in order_items)
    
    print(f"Debug: Total items: {total_items}, Total weight: {total_weight}")

    # Check for specific SKU quantities
    sku_80510_count = sum(safe_float(item.get('Quantity', 0)) for item in order_items if item.get('Product', {}).get('SKU') == '80510')
    sku_80511_count = sum(safe_float(item.get('Quantity', 0)) for item in order_items if item.get('Product', {}).get('SKU') == '80511')

    print(f"Debug: SKU 80510 count: {sku_80510_count}, SKU 80511 count: {sku_80511_count}")

    if sku_80510_count == 1 or sku_80511_count == 1:
        print("Debug: Condition met for SKU 80510/80511 count == 1")
        return '3005', f"1x SKU 80510/80511"
    elif sku_80510_count == 2:
        return '3006', "2x SKU 80510"
    elif sku_80510_count == 3:
        return '3008', "3x SKU 80510"
    elif sku_80511_count == 2:
        return '3005', "2x SKU 80511"
    elif sku_80511_count == 3:
        return '3006', "3x SKU 80511"

    # Other allocation rules
    if total_items == 1:
        print("Debug: Condition met for total_items == 1")
        return '3001', "1 item"
    
    # ... rest of the function remains the same
