from box_allocation import allocate_box

def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def process_orders(orders_data):
    processed_orders = []
    
    for order in orders_data:
        total_weight = sum(
            safe_float(item.get('Product', {}).get('Weight', 0)) * safe_float(item.get('Quantity', 0))
            for item in order.get('OrderItems', [])
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
                for item in order.get('OrderItems', [])
            ]
        }
        
        processed_order['allocated_box'] = allocate_box(order)
        processed_orders.append(processed_order)
    
    return processed_orders
