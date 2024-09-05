import streamlit as st
from datetime import datetime, timedelta, date
from collections import Counter
from billbee_api import BillbeeAPI
from box_allocation import allocate_box
from data_processor import process_orders
from inventory_management import update_box_inventory, get_box_inventory, initialize_inventory_if_empty, adjust_inventory_for_usage
from s3_operations import get_summary_data, update_box_usage, get_s3_fs, clear_order_data
import pandas as pd
import traceback

# Initialisierung der Billbee API
billbee_api = BillbeeAPI()

# Initialisiere Inventar, falls es leer ist
initialize_inventory_if_empty()

# Lade das aktuelle Inventar
inventory = get_box_inventory()

# Add this dictionary at the top of the file, after the imports
BOX_URLS = {
    '3002': 'https://www.karton.eu/300x215x100-mm-einwellige-Kartons',
    '3003': 'https://www.karton.eu/300x215x140-mm-einwellige-Kartons',
    '3004': 'https://www.karton.eu/250x250x250-mm-einwellige-Kartons'
}

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

        # Überprüfe, ob bereits Daten für diesen Tag existieren
        existing_usage = get_daily_usage(process_date)
        if existing_usage:
            st.info(f"Daten für {process_date} existieren bereits. Überspringe Verarbeitung.")
            return []

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
def update_data(processed_orders):
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    filename = "processed_orders.csv"
    full_path = f"{bucket_name}/{filename}"
    
    df = pd.DataFrame(processed_orders)
    
    with s3.open(full_path, 'w') as f:
        df.to_csv(f, index=False)
    
    st.success(f"{len(processed_orders)} Bestellungen verarbeitet und gespeichert.")

# Hauptfunktion der App
def main():
    st.title("Kartonverwaltungs-App")

    # Erstelle Tabs
    tab1, tab2, tab3 = st.tabs(["Hauptansicht", "Bestandsverwaltung", "Bestellzuordnungen"])

    with tab1:
        clear_data = st.checkbox("Vorhandene Bestelldaten löschen")
        if st.button("Daten aktualisieren"):
            if clear_data:
                clear_order_data()
                st.success("Vorhandene Bestelldaten wurden gelöscht.")
            
            with st.spinner('Daten werden aktualisiert...'):
                processed_orders = fetch_and_process_orders()
            
            if processed_orders:
                update_data(processed_orders)
            else:
                st.info("Keine neuen Daten zu verarbeiten.")

        # Anzeige der Bestandsreichweite und Warnungen
        st.subheader("Bestandsreichweite")
        display_inventory_summary()

    with tab2:
        # Bestandsverwaltung
        st.subheader("Aktueller Kartonbestand")
        display_current_inventory()

        st.subheader("Bestand aktualisieren")
        update_inventory_ui()

    with tab3:
        # Bestellzuordnungen anzeigen
        st.subheader("Zuordnungen der letzten 50 Bestellungen")
        display_order_allocations()

def display_order_allocations():
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    filename = "processed_orders.csv"
    full_path = f"{bucket_name}/{filename}"
    
    if s3.exists(full_path):
        with s3.open(full_path, 'r') as f:
            orders = pd.read_csv(f)
        orders = orders.sort_values('created_at', ascending=False).head(50)
        
        for _, order in orders.iterrows():
            products_str = ", ".join([f"{p['sku']} (x{p['quantity']})" for p in eval(order['products'])])
            st.write(f"Bestellnummer: {order['order_number']}, Karton: {order['allocated_box']}, Grund: {order['allocation_reason']}")
            st.write(f"Produkte: {products_str}")
            st.write(f"Gesamtgewicht: {order['total_weight'] / 1000:.2f} kg")
            st.write("---")
    else:
        st.info("Keine verarbeiteten Bestellungen gefunden.")

# Funktion zur Anzeige der Bestandsübersicht
def display_inventory_summary():
    try:
        summary_data = get_summary_data()
        if not summary_data.empty:
            # Add a new column for the URL
            summary_data['Order URL'] = summary_data['Kartontyp'].apply(
                lambda x: f"[Bestellen]({BOX_URLS[str(x)]})" if str(x) in BOX_URLS else ""
            )
            
            # Reorder columns to put the new columns in the desired position
            cols = ['Kartontyp', 'Produktname'] + [col for col in summary_data.columns if col not in ['Kartontyp', 'Produktname', 'Order URL']] + ['Order URL']
            summary_data = summary_data[cols]
            
            # Display the dataframe
            st.markdown(summary_data.to_markdown(index=False), unsafe_allow_html=True)
            
            for _, row in summary_data.iterrows():
                days_left = float(row['Reichweite (Tage)'].replace(',', '.'))
                kartontyp = row['Kartontyp']
                produktname = row['Produktname']
                if days_left < 30:
                    st.warning(f"Warnung: Bestand für {kartontyp} ({produktname}) reicht nur noch für {days_left:.1f} Tage!")
        else:
            st.info("Keine Daten zur Bestandsreichweite verfügbar.")
    except Exception as e:
        st.error(f"Fehler beim Abrufen der Bestandsreichweite: {str(e)}")
        st.error(f"Stacktrace: {traceback.format_exc()}")

# Funktion zur Anzeige des aktuellen Inventars
def display_current_inventory():
    inventory = get_current_inventory()
    for box_type, data in inventory.items():
        quantity = data.get('quantity', 'Nicht verfügbar')
        last_updated = data.get('last_updated', 'Nicht verfügbar')
        st.write(f"{box_type}: {quantity} (Zuletzt aktualisiert: {last_updated})")

# Funktion zur Aktualisierung des Inventars über die UI
def update_inventory_ui():
    global inventory
    inventory = get_current_inventory()
    
    st.subheader("Bestand aktualisieren")
    update_option = st.radio("Aktion wählen", ["Bestand aktualisieren", "Neue SKU hinzufügen"])
    
    if update_option == "Bestand aktualisieren":
        box_type = st.selectbox("Kartontyp", options=list(inventory.keys()))
        new_quantity = st.number_input("Neuer Bestand", step=1, value=int(inventory[box_type]['quantity']))
    else:  # Neue SKU hinzufügen
        box_type = st.text_input("Neue SKU")
        new_quantity = st.number_input("Anfangsbestand", step=1, min_value=0, value=0)
    
    update_date = st.date_input("Aktualisierungsdatum", value=datetime.now().date())
    
    if st.button("Bestand aktualisieren" if update_option == "Bestand aktualisieren" else "Neue SKU hinzufügen"):
        update_box_inventory(box_type, new_quantity, update_date)
        if update_option == "Bestand aktualisieren":
            st.success(f"Bestand für {box_type} aktualisiert.")
        else:
            st.success(f"Neue SKU {box_type} hinzugefügt.")
        # Aktualisiere das Inventar nach der Änderung
        inventory = get_box_inventory()

def get_current_inventory():
    return get_box_inventory()

# Add this function near the other data-related functions
def get_daily_usage(date):
    s3 = get_s3_fs()
    bucket_name = st.secrets['aws']['S3_BUCKET_NAME']
    usage_file = "daily_box_usage.csv"
    usage_path = f"{bucket_name}/{usage_file}"

    if s3.exists(usage_path):
        with s3.open(usage_path, 'r') as f:
            df = pd.read_csv(f)
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df[df['date'] == date].to_dict('records')
    return []

if __name__ == "__main__":
    main()
