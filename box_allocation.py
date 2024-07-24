def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def allocate_box(order):
    order_items = order.get('OrderItems', [])
    total_items = sum(safe_float(item.get('Quantity', 0)) for item in order_items)
    total_weight = sum(
        safe_float(item.get('Product', {}).get('Weight', 0)) * safe_float(item.get('Quantity', 0))
        for item in order_items
    )
    special_skus = ['8000', '8001', '8002', '8003', '8004']

    # Überprüfe auf spezielle SKUs
    special_sku_count = sum(
        1 for item in order_items 
        if item.get('Product', {}).get('SKU') in special_skus
    )

    if special_sku_count > 0:
        return '3002' * special_sku_count

    # Andere Zuordnungsregeln
    if total_items == 1 and total_weight <= 2:
        return '3001'
    elif total_items == 2 and total_weight <= 3:
        return '3002'
    elif 3 <= total_items <= 4 and total_weight <= 6:
        return '3003'
    elif any(item.get('Product', {}).get('SKU') == '80533' for item in order_items):
        return '3004'
    elif (5 <= total_items <= 10 and total_weight <= 10) or \
         any(item.get('Product', {}).get('SKU') == '80510' and safe_float(item.get('Quantity', 0)) == 1 for item in order_items) or \
         any(item.get('Product', {}).get('SKU') == '80511' and safe_float(item.get('Quantity', 0)) == 2 for item in order_items):
        return '3005'
    elif any(item.get('Product', {}).get('SKU') == '80510' and safe_float(item.get('Quantity', 0)) == 2 for item in order_items):
        return '3006'
    elif any(item.get('Product', {}).get('SKU') == '80510' and safe_float(item.get('Quantity', 0)) == 3 for item in order_items):
        return '3008'

    # Wenn keine Zuordnung möglich ist
    return None
