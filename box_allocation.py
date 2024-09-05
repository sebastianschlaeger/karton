def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def allocate_box(total_weight):
    if total_weight <= 1800:
        return '3001', 'Weight <= 1800g'
    elif total_weight <= 3000:
        return '3002', '1800g < Weight <= 3000g'
    elif total_weight <= 5300:
        return '3003', '3000g < Weight <= 5300g'
    elif total_weight <= 10200:
        return '3005', '5300g < Weight <= 10200g'
    elif total_weight <= 20200:
        return '3006', '10200g < Weight <= 20200g'
    else:
        return '3008', 'Weight > 20200g'

    # Special case for SKU 80533
    if any(item.get('Product', {}).get('SKU') == '80533' for item in order_items):
        return '3004', 'Special case for SKU 80533'