import streamlit as st
from datetime import datetime, timedelta, date
from collections import Counter
from billbee_api import BillbeeAPI
from box_allocation import allocate_box
from data_processor import process_orders
from inventory_management import update_box_inventory, get_box_inventory, initialize_inventory_if_empty, adjust_inventory_for_usage
from s3_operations import save_unallocated_orders, get_unallocated_orders, get_summary_data, update_box_usage, get_s3_fs, clear_order_data
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
    usage_file = "daily_box_usage.csv"
    usage_path = f"{bucket_name}/{usage_file}"

    today = datetime.now().date()
    end_date = today - timedelta(days=1)  # Letzter voller Tag
    start_date = end_date - timedelta(days=29)  # 30 Tage zurück

    existing_data = pd.DataFrame(columns=['date', 'box_type', 'quantity'])
    if s3.exists(usage_path):
        with s3.open(usage_path, 'r') as f:
            existing_data = pd.read_csv(f)
        existing_data['date'] = pd.to_datetime(existing_data['date']).dt.date

    date_range = pd.date_range(start_date, end_date, freq='D')
    missing_dates = [d.date() for d in date_range if d.date() not in existing_data['date'].unique()]

    st.info(f"Startdatum: {start_date}, Enddatum: {end_date}")
    st.info(f"Anzahl fehlender Tage: {len(missing_dates)}")

    if not missing_dates:
        st.info("Alle Daten für die letzten 30 Tage sind bereits vorhanden.")
        return []

    all_processed_orders = []
    total_days = len(missing_dates)
    
    progress_bar = st.progress(0)
    
    for i, current_date in enumerate(missing_dates):
        st.info(f"Verarbeite Bestellungen für {current_date}")
        daily_orders = fetch_and_process_daily_orders(current_date)
        all_processed_orders.extend(daily_orders)
        
        progress = (i + 1) / total_days
        progress_bar.progress(progress)
        
        st.info(f"Fortschritt: {i+1}/{total_days} Tage verarbeitet")

    progress_bar.empty()
    st.success(f"Insgesamt {len(all_processed_orders)} Bestellungen verarbeitet.")
    return all_processed_orders

def fetch_and_process_daily_orders(process_date):
    try:
        if not isinstance(process_date, date):
            raise ValueError(f"Ungültiges Datumsformat: {process_date}")
        
        orders_data = billbee_api.get_orders(process_date, process_date + timedelta(days=1))
        st.info(f"Anzahl der abgerufenen Bestellungen für {process_date}: {len(orders_data)}")
        
        processed_orders = process_orders(orders_data)
        st.info(f"Anzahl der verarbeiteten Bestellungen für {process_date}: {len(processed_orders)}")

        # Summiere den Kartonverbrauch für diesen Tag
        daily_usage = Counter()
        for order in processed_orders:
            if order['allocated_box']:
                daily_usage[order['allocated_box']] += 1

        # Speichere die tägliche Zusammenfassung
        for box_type, quantity in daily_usage.items():
            update_box_usage(box_type, quantity, process_date)

        return processed_orders
    except Exception as e:
        st.error(f"Fehler beim Abrufen oder Verarbeiten der Bestellungen für {process_date}: {str(e)}")
        st.error(f"Stacktrace: {traceback.format_exc()}")
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
        order_date = datetime.strptime(order['created_at'], "%Y-%m-%dT%H:%M:%S").date()
        if allocated_box:
            allocated_orders.append((order, allocated_box))
            update_box_usage(allocated_box, 1, order_date)  # Übergebe das Bestelldatum
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
    for order, box in allocated_orders[-50:]:
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
    with st.spinner('Daten werden aktualisiert...'):
        processed_orders = fetch_and_process_orders()
        update_data(processed_orders)

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
    if not summary_data.empty:
        st.dataframe(summary_data.set_index("Kartontyp"))
        
        for _, row in summary_data.iterrows():
            days_left = float(row['Reichweite (Tage)'].replace(',', '.'))
            if days_left < 30:
                st.warning(f"Warnung: Bestand für {row['Kartontyp']} reicht nur noch für {days_left:.1f} Tage!")
    else:
        st.info("Keine Daten zur Bestandsreichweite verfügbar.")
except Exception as e:
    st.error(f"Fehler beim Abrufen der Bestandsreichweite: {str(e)}")
    st.error("Details zum DataFrame:")
    st.write(summary_data.dtypes)
    st.write(summary_data.head())

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

def summarize_daily_usage():
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    usage_file = "daily_box_usage.csv"
    usage_path = f"{bucket_name}/{usage_file}"
    
    if s3.exists(usage_path):
        with s3.open(usage_path, 'r') as f:
            usage_data = pd.read_csv(f)
        
        # Konvertiere das Datum in datetime
        usage_data['date'] = pd.to_datetime(usage_data['date'])
        
        # Gruppiere nach Datum und Kartontyp, summiere die Mengen
        daily_summary = usage_data.groupby(['date', 'box_type'])['quantity'].sum().reset_index()
        
        # Sortiere nach Datum (neueste zuerst) und Kartontyp
        daily_summary = daily_summary.sort_values(['date', 'box_type'], ascending=[False, True])
        
        # Speichere die aktualisierte Zusammenfassung
        with s3.open(usage_path, 'w') as f:
            daily_summary.to_csv(f, index=False)
        
        return daily_summary
    else:
        return pd.DataFrame(columns=['date', 'box_type', 'quantity'])

# Anzeige des täglichen Verbrauchs
st.subheader("Täglicher Verbrauch")
try:
    daily_usage = summarize_daily_usage()
    if not daily_usage.empty:
        st.dataframe(daily_usage)
    else:
        st.info("Keine täglichen Verbrauchsdaten verfügbar.")
except Exception as e:
    st.error(f"Fehler beim Abrufen der täglichen Verbrauchsdaten: {str(e)}")

st.sidebar.info("Diese App verwaltet den Kartonbestand und zeigt Warnungen für niedrige Bestände an.")
