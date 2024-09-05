from box_allocation import allocate_box

def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def process_orders(orders_data):
    processed_orders = []
    
    for order in orders_data:
        if not isinstance(order, dict):
            print(f"Warning: Skipping invalid order data: {order}")
            continue

        valid_items = [item for item in order.get('OrderItems', []) if isinstance(item, dict) and item.get('Product') is not None]
        
        if not valid_items:
            continue  # Skip orders without valid products
        
        total_weight = sum(
            safe_float(item.get('Product', {}).get('Weight', 0)) * safe_float(item.get('Quantity', 0))
            for item in valid_items
        )
        
        processed_order = {
            'order_number': order.get('OrderNumber', 'Unknown'),
            'created_at': order.get('CreatedAt'),
            'total_weight': total_weight,  # Stellen Sie sicher, dass dies korrekt ist
            'products': [
                {
                    'sku': item.get('Product', {}).get('SKU', 'Unknown'),
                    'quantity': safe_float(item.get('Quantity', 0)),
                    'weight': safe_float(item.get('Product', {}).get('Weight', 0))
                }
                for item in valid_items
            ],
            'OrderItems': valid_items
        }
        
        # Check for special case SKU 80533
        has_special_sku = any(item.get('Product', {}).get('SKU') == '80533' for item in valid_items)

        if has_special_sku:
            allocated_box, allocation_reason = '3004', 'Special case for SKU 80533'
        else:
            allocated_box, allocation_reason = allocate_box(total_weight)

        processed_order['allocated_box'] = allocated_box
        processed_order['allocation_reason'] = allocation_reason
        processed_orders.append(processed_order)
    
    return processed_orders
