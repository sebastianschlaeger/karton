def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def allocate_box(total_weight):
    if total_weight <= 500:
        return '3001', 'Weight <= 500g'
    elif total_weight <= 1000:
        return '3002', '500g < Weight <= 1000g'
    elif total_weight <= 2000:
        return '3003', '1000g < Weight <= 2000g'
    elif total_weight <= 5000:
        return '3004', '2000g < Weight <= 5000g'
    elif total_weight <= 10000:
        return '3005', '5000g < Weight <= 10000g'
    elif total_weight <= 20000:
        return '3006', '10000g < Weight <= 20000g'
    else:
        return '3008', 'Weight > 20000g'

    # Special case for SKU 80533
    if any(item.get('Product', {}).get('SKU') == '80533' for item in order_items):
        return '3004', 'Special case for SKU 80533'