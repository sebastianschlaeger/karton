import streamlit as st
from datetime import datetime, timedelta
from billbee_api import BillbeeAPI
from box_allocation import allocate_box
from data_processor import process_orders
from inventory_management import update_box_inventory, get_box_inventory
from s3_operations import save_unallocated_orders, get_unallocated_orders, get_summary_data, update_box_usage

st.title("Kartonverwaltungs-App")

# Initialisierung der Billbee API
billbee_api = BillbeeAPI()

# Funktion zum Abrufen und Verarbeiten von Bestellungen
def fetch_and_process_orders():
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=2)
    orders_data = billbee_api.get_orders_for_date_range(start_date, end_date)
    processed_orders = process_orders(orders_data)
    return processed_orders

# Hauptfunktion zum Aktualisieren der Daten
def update_data():
    processed_orders = fetch_and_process_orders()
    allocated_orders = []
    unallocated_orders = []

    for order in processed_orders:
        allocated_box = order['allocated_box']
        if allocated_box:
            allocated_orders.append((order, allocated_box))
        else:
            unallocated_orders.append(order)

    # Aktualisiere Kartonbestand und Nutzung
    for order, box_type in allocated_orders:
        update_box_inventory(box_type, -1)  # Reduziere Bestand um 1
        update_box_usage(box_type, 1)  # Erhöhe Nutzung um 1

    # Speichere nicht zuordenbare Bestellungen
    if unallocated_orders:
        save_unallocated_orders(unallocated_orders)

    st.success(f"{len(allocated_orders)} Bestellungen verarbeitet. {len(unallocated_orders)} nicht zuordenbare Bestellungen gefunden.")

# UI-Elemente
if st.button("Daten aktualisieren"):
    update_data()

# Anzeige des aktuellen Kartonbestands
st.subheader("Aktueller Kartonbestand")
inventory = get_box_inventory()
for box_type, quantity in inventory.items():
    st.write(f"{box_type}: {quantity}")

# Bestandsaktualisierung
st.subheader("Bestand aktualisieren")
box_type = st.selectbox("Kartontyp", options=list(inventory.keys()))
quantity_change = st.number_input("Mengenänderung", step=1)
if st.button("Bestand aktualisieren"):
    update_box_inventory(box_type, quantity_change)
    st.success(f"Bestand für {box_type} aktualisiert.")

# Anzeige der Bestandsreichweite und Warnungen
st.subheader("Bestandsreichweite")
summary_data = get_summary_data()
for box_type, data in summary_data.items():
    days_left = data['days_left']
    st.write(f"{box_type}: {days_left:.1f} Tage")
    if days_left < 30:
        st.warning(f"Warnung: Bestand für {box_type} reicht nur noch für {days_left:.1f} Tage!")

# Anzeige nicht zuordenbarer Bestellungen
st.subheader("Nicht zuordenbare Bestellungen")
unallocated_orders = get_unallocated_orders()
if unallocated_orders:
    for order in unallocated_orders:
        products_str = ", ".join([f"{p['sku']} (x{p['quantity']})" for p in order['products']])
        st.write(f"Bestellnummer: {order['order_number']}, Produkte: {products_str}")
else:
    st.info("Keine nicht zuordenbaren Bestellungen gefunden.")

# Funktion zur Anpassung der Kartonzuordnungsregeln
st.subheader("Kartonzuordnungsregeln anpassen")
st.write("Diese Funktion ist noch in Entwicklung. In Zukunft können Sie hier die Zuordnungsregeln anpassen.")

st.sidebar.info("Diese App verwaltet den Kartonbestand und zeigt Warnungen für niedrige Bestände an.")
