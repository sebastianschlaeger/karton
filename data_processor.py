from box_allocation import allocate_box

def process_orders(orders_data):
    processed_orders = []
    
    for order in orders_data:
        processed_order = {
            'order_number': order['OrderNumber'],
            'created_at': order['CreatedAt'],
            'total_weight': sum(item['Product']['Weight'] * item['Quantity'] for item in order['OrderItems']),
            'products': [
                {
                    'sku': item['Product']['SKU'],
                    'quantity': item['Quantity'],
                    'weight': item['Product']['Weight']
                }
                for item in order['OrderItems']
            ]
        }
        
        processed_order['allocated_box'] = allocate_box(order)
        processed_orders.append(processed_order)
    
    return processed_orders
