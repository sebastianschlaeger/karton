def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def allocate_box(order):
    if isinstance(order, str):
        return None, "Invalid order data: received string instead of dictionary"

    order_items = order.get('OrderItems', [])
    if not order_items:
        return None, "No order items found"

    total_weight = sum(
        safe_float(item.get('Product', {}).get('WeightInGram', 0)) * safe_float(item.get('Quantity', 0))
        for item in order_items
    )
    total_weight_kg = total_weight / 1000  # Convert to kg

    print(f"Debug: Total weight: {total_weight_kg:.2f} kg")

    # Check for SKU 80533
    if any(item.get('Product', {}).get('SKU') == '80533' and safe_float(item.get('Quantity', 0)) == 1 for item in order_items):
        return '3004', "Contains 1x SKU 80533"

    # Allocate box based on weight
    if total_weight_kg < 1.8:
        return '3001', f"Weight: {total_weight_kg:.2f} kg"
    elif 1.8 <= total_weight_kg < 3:
        return '3002', f"Weight: {total_weight_kg:.2f} kg"
    elif 3 <= total_weight_kg < 5.3:
        return '3003', f"Weight: {total_weight_kg:.2f} kg"
    elif 5.3 <= total_weight_kg < 10.2:
        return '3005', f"Weight: {total_weight_kg:.2f} kg"
    elif 10.2 <= total_weight_kg < 20.2:
        return '3006', f"Weight: {total_weight_kg:.2f} kg"
    elif 20.2 <= total_weight_kg <= 31.5:
        return '3008', f"Weight: {total_weight_kg:.2f} kg"
    else:
        return None, f"Weight exceeds maximum: {total_weight_kg:.2f} kg"