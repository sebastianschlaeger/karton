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
    special_sku_count = sum(
        1 for item in order_items 
        if item.get('Product', {}).get('SKU') in special_skus
    )

    if special_sku_count > 0:
        return '3002' * special_sku_count

    # Check for specific SKU quantities
    sku_80510_count = sum(safe_float(item.get('Quantity', 0)) for item in order_items if item.get('Product', {}).get('SKU') == '80510')
    sku_80511_count = sum(safe_float(item.get('Quantity', 0)) for item in order_items if item.get('Product', {}).get('SKU') == '80511')

    if sku_80510_count == 2:
        return '3006'
    elif sku_80510_count == 3:
        return '3008'
    elif sku_80511_count == 2:
        return '3005'
    elif sku_80511_count == 3:
        return '3006'

    # Other allocation rules
    if total_items == 1:
        return '3001'
    elif total_items == 2:
        return '3002'
    elif 3 <= total_items <= 4:
        return '3003'
    elif any(item.get('Product', {}).get('SKU') == '80533' for item in order_items):
        return '3004'
    elif (5 <= total_items <= 10 and total_weight <= 10) or \
         (sku_80510_count == 1) or \
         (sku_80511_count == 1):
        return '3005'

    # If no allocation is possible
    return None
