def allocate_box(order):
    total_items = sum(item['Quantity'] for item in order['OrderItems'])
    total_weight = sum(item['Product']['Weight'] * item['Quantity'] for item in order['OrderItems'])
    special_skus = ['8000', '8001', '8002', '8003', '8004']

    # Überprüfe auf spezielle SKUs
    special_sku_count = sum(1 for item in order['OrderItems'] if item['Product']['SKU'] in special_skus)

    if special_sku_count > 0:
        return '3002' * special_sku_count

    # Andere Zuordnungsregeln
    if total_items == 1 and total_weight <= 2:
        return '3001'
    elif total_items == 2 and total_weight <= 3:
        return '3002'
    elif 3 <= total_items <= 4 and total_weight <= 6:
        return '3003'
    elif any(item['Product']['SKU'] == '80533' for item in order['OrderItems']):
        return '3004'
    elif (5 <= total_items <= 10 and total_weight <= 10) or \
         any(item['Product']['SKU'] == '80510' and item['Quantity'] == 1 for item in order['OrderItems']) or \
         any(item['Product']['SKU'] == '80511' and item['Quantity'] == 2 for item in order['OrderItems']):
        return '3005'
    elif any(item['Product']['SKU'] == '80510' and item['Quantity'] == 2 for item in order['OrderItems']):
        return '3006'
    elif any(item['Product']['SKU'] == '80510' and item['Quantity'] == 3 for item in order['OrderItems']):
        return '3008'

    # Wenn keine Zuordnung möglich ist
    return None
