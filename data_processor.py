from box_allocation import allocate_box

def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def process_orders(orders_data):
    processed_orders = []
    
    for order in orders_data:
        valid_items = [item for item in order.get('OrderItems', []) if item.get('Product') is not None]
        
        if not valid_items:
            continue  # Überspringe Bestellungen ohne gültige Produkte
        
        total_weight = sum(
            safe_float(item.get('Product', {}).get('Weight', 0)) * safe_float(item.get('Quantity', 0))
            for item in valid_items
        )
        
        processed_order = {
            'order_number': order.get('OrderNumber', 'Unknown'),
            'created_at': order.get('CreatedAt'),
            'total_weight': total_weight,
            'products': [
                {
                    'sku': item.get('Product', {}).get('SKU', 'Unknown'),
                    'quantity': safe_float(item.get('Quantity', 0)),
                    'weight': safe_float(item.get('Product', {}).get('Weight', 0))
                }
                for item in valid_items
            ]
        }
        
        processed_order['allocated_box'] = allocate_box(order)
        processed_orders.append(processed_order)
    
    return processed_orders
