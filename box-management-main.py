import streamlit as st
from datetime import datetime, timedelta
from collections import Counter
from billbee_api import BillbeeAPI
from box_allocation import allocate_box
from data_processor import process_orders
from inventory_management import update_box_inventory, get_box_inventory, initialize_inventory_if_empty, adjust_inventory_for_usage
from s3_operations import save_unallocated_orders, get_unallocated_orders, get_summary_data, update_box_usage, summarize_daily_usage

st.title("Kartonverwaltungs-App")

# Initialisierung der Billbee API
billbee_api = BillbeeAPI()

# Initialisiere Inventar, falls es leer ist
initialize_inventory_if_empty()

# Lade das aktuelle Inventar
inventory = get_box_inventory()

# Funktion zum Abrufen und Verarbeiten von Bestellungen
def fetch_and_process_orders():
    orders_data = billbee_api.get_last_50_orders()
    processed_orders = process_orders(orders_data)
    return processed_orders

# Funktion zur Berechnung des Verbrauchs pro Karton-Art
def calculate_box_usage(allocated_orders):
    usage_counter = Counter()
    for order, box in allocated_orders:
        usage_counter[box] += 1
    return usage_counter

# Hauptfunktion zum Aktualisieren der Daten
def update_data():
    processed_orders = fetch_and_process_orders()
    allocated_orders = []
    unallocated_orders = []

    for order in processed_orders:
        allocated_box = order['allocated_box']
        if allocated_box:
            allocated_orders.append((order, allocated_box))
            update_box_usage(allocated_box, 1)  # Erhöhe Nutzung um 1
        else:
            unallocated_orders.append(order)

    # Berechne Verbrauch pro Karton-Art
    box_usage = calculate_box_usage(allocated_orders)

    # Speichere nicht zuordenbare Bestellungen
    if unallocated_orders:
        save_unallocated_orders(unallocated_orders)

    st.success(f"{len(allocated_orders)} Bestellungen verarbeitet. {len(unallocated_orders)} nicht zuordenbare Bestellungen gefunden.")
    
    # Anzeige der Verbrauchsübersicht
    st.subheader("Verbrauch pro Karton-Art")
    for box_type, count in box_usage.items():
        st.write(f"{box_type}: {count}")
    
    # Anzeige der Zuordnungen
    st.subheader("Zuordnungen der letzten 50 Bestellungen")
    for order, box in allocated_orders:
        products_str = ", ".join([f"{p['sku']} (x{p['quantity']})" for p in order['products']])
        st.write(f"Bestellnummer: {order['order_number']}, Karton: {box}, Produkte: {products_str}")
    
    # Anzeige nicht zuordenbarer Bestellungen
    st.subheader("Nicht zuordenbare Bestellungen")
    if unallocated_orders:
        for order in unallocated_orders:
            products_str = ", ".join([f"{p['sku']} (x{p['quantity']})" for p in order['products']])
            st.write(f"Bestellnummer: {order['order_number']}, Produkte: {products_str}")
    else:
        st.info("Keine nicht zuordenbaren Bestellungen gefunden.")

# UI-Elemente
if st.button("Daten aktualisieren"):
    update_data()

# Anzeige des aktuellen Kartonbestands
st.subheader("Aktueller Kartonbestand")
for box_type, data in inventory.items():
    st.write(f"{box_type}: {data['quantity']} (Zuletzt aktualisiert: {data['last_updated']})")

# Bestandsaktualisierung
st.subheader("Bestand aktualisieren")
box_type = st.selectbox("Kartontyp", options=list(inventory.keys()))
quantity_change = st.number_input("Mengenänderung", step=1)
if st.button("Bestand aktualisieren"):
    adjust_inventory_for_usage()
    update_box_inventory(box_type, quantity_change)
    st.success(f"Bestand für {box_type} aktualisiert.")
    # Aktualisiere das Inventar nach der Änderung
    inventory = get_box_inventory()

# Anzeige der Bestandsreichweite und Warnungen
st.subheader("Bestandsreichweite")
summary_data = get_summary_data()
for box_type, data in summary_data.items():
    days_left = data['days_left']
    st.write(f"{box_type}: {days_left:.1f} Tage")
    if days_left < 30:
        st.warning(f"Warnung: Bestand für {box_type} reicht nur noch für {days_left:.1f} Tage!")

# Anzeige des täglichen Verbrauchs
st.subheader("Täglicher Verbrauch")
summarize_daily_usage()  # Aktualisiere die tägliche Zusammenfassung
s3 = get_s3_fs()
bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
summary_file = "daily_box_usage.csv"
summary_path = f"{bucket_name}/{summary_file}"

if s3.exists(summary_path):
    with s3.open(summary_path, 'r') as f:
        daily_usage = pd.read_csv(f)
    daily_usage['date'] = pd.to_datetime(daily_usage['date']).dt.date
    daily_usage = daily_usage.sort_values(['date', 'box_type'], ascending=[False, True])
    st.dataframe(daily_usage)
else:
    st.info("Keine täglichen Verbrauchsdaten verfügbar.")

st.sidebar.info("Diese App verwaltet den Kartonbestand und zeigt Warnungen für niedrige Bestände an.")
