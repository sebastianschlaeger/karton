import streamlit as st
from datetime import datetime, timedelta
from collections import Counter
from billbee_api import BillbeeAPI
from box_allocation import allocate_box
from data_processor import process_orders
from inventory_management import update_box_inventory, get_box_inventory, initialize_inventory_if_empty, adjust_inventory_for_usage
from s3_operations import save_unallocated_orders, get_unallocated_orders, get_summary_data, update_box_usage, summarize_daily_usage, get_s3_fs, clear_order_data
import pandas as pd

st.title("Kartonverwaltungs-App")

# Initialisierung der Billbee API
billbee_api = BillbeeAPI()

# Initialisiere Inventar, falls es leer ist
initialize_inventory_if_empty()

# Lade das aktuelle Inventar
inventory = get_box_inventory()

# Funktion zum Abrufen und Verarbeiten von Bestellungen
def fetch_and_process_orders():
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    last_import_file = "last_import_date.txt"
    last_import_path = f"{bucket_name}/{last_import_file}"

    today = datetime.now().date()
    
    if s3.exists(last_import_path):
        with s3.open(last_import_path, 'r') as f:
            last_import_date = datetime.strptime(f.read().strip(), "%Y-%m-%d").date()
    else:
        last_import_date = today - timedelta(days=30)

    end_date = today - timedelta(days=1)
    
    st.info(f"Letztes Importdatum: {last_import_date}, Enddatum: {end_date}")

    if last_import_date >= end_date:
        st.info("Alle verfügbaren Daten wurden bereits importiert.")
        return []

    start_date = last_import_date + timedelta(days=1)
    st.info(f"Importiere Bestellungen von {start_date} bis {end_date}")
    
    try:
        orders_data = billbee_api.get_orders(start_date, end_date)
        st.info(f"Anzahl der abgerufenen Bestellungen: {len(orders_data)}")
        
        processed_orders = process_orders(orders_data)
        st.info(f"Anzahl der verarbeiteten Bestellungen: {len(processed_orders)}")

        # Update last import date
        with s3.open(last_import_path, 'w') as f:
            f.write(end_date.strftime("%Y-%m-%d"))

        return processed_orders
    except Exception as e:
        st.error(f"Fehler beim Abrufen oder Verarbeiten der Bestellungen: {str(e)}")
        return []

# Funktion zur Berechnung des Verbrauchs pro Karton-Art
def calculate_box_usage(allocated_orders):
    usage_counter = Counter()
    for order, box in allocated_orders:
        usage_counter[box] += 1
    return usage_counter

# Hauptfunktion zum Aktualisieren der Daten
def update_data(clear_existing_data=False):
    if clear_existing_data:
        clear_order_data()
        st.success("Vorhandene Bestelldaten wurden gelöscht.")
    
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
clear_data = st.checkbox("Vorhandene Bestelldaten löschen")
if st.button("Daten aktualisieren"):
    update_data(clear_data)

# Anzeige des aktuellen Kartonbestands
st.subheader("Aktueller Kartonbestand")
for box_type, data in inventory.items():
    quantity = data.get('quantity', 'Nicht verfügbar')
    last_updated = data.get('last_updated', 'Nicht verfügbar')
    st.write(f"{box_type}: {quantity} (Zuletzt aktualisiert: {last_updated})")

# Bestandsaktualisierung
st.subheader("Bestand aktualisieren")
box_type = st.selectbox("Kartontyp", options=list(inventory.keys()))
new_quantity = st.number_input("Neuer Bestand", step=1, value=int(inventory[box_type]['quantity']))
update_date = st.date_input("Aktualisierungsdatum", value=datetime.now().date())
if st.button("Bestand aktualisieren"):
    update_box_inventory(box_type, new_quantity, update_date)
    st.success(f"Bestand für {box_type} aktualisiert.")
    # Aktualisiere das Inventar nach der Änderung
    inventory = get_box_inventory()

# Anzeige der Bestandsreichweite und Warnungen
st.subheader("Bestandsreichweite")
try:
    summary_data = get_summary_data()
    data = []
    for box_type, info in summary_data.items():
        data.append({
            "Kartontyp": box_type,
            "Ursprünglicher Bestand": int(info['original_quantity']),
            "Verbrauch (letzte 30 Tage)": int(info['usage_last_30_days']),
            "Aktueller Bestand": int(info['current_quantity']),
            "Reichweite (Tage)": f"{info['days_left']:.1f}"
        })
        if info['days_left'] < 30:
            st.warning(f"Warnung: Bestand für {box_type} reicht nur noch für {info['days_left']:.1f} Tage!")
    
    df = pd.DataFrame(data)
    st.table(df.set_index("Kartontyp"))
except Exception as e:
    st.error(f"Fehler beim Abrufen der Bestandsreichweite: {str(e)}")

def reset_last_import_date():
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    last_import_file = "last_import_date.txt"
    last_import_path = f"{bucket_name}/{last_import_file}"
    
    reset_date = datetime.now().date() - timedelta(days=30)
    
    with s3.open(last_import_path, 'w') as f:
        f.write(reset_date.strftime("%Y-%m-%d"))
    
    st.success(f"Letztes Importdatum wurde auf {reset_date} zurückgesetzt.")

if st.button("Importdatum zurücksetzen"):
    reset_last_import_date()

# Anzeige des täglichen Verbrauchs
st.subheader("Täglicher Verbrauch")
try:
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
except Exception as e:
    st.error(f"Fehler beim Abrufen der täglichen Verbrauchsdaten: {str(e)}")

st.sidebar.info("Diese App verwaltet den Kartonbestand und zeigt Warnungen für niedrige Bestände an.")
