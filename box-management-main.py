import requests
from datetime import datetime, timedelta
import streamlit as st

class BillbeeAPI:
    BASE_URL = "https://api.billbee.io/api/v1"

    def __init__(self):
        self.api_key = st.secrets["billbee"]["API_KEY"]
        self.username = st.secrets["billbee"]["USERNAME"]
        self.password = st.secrets["billbee"]["PASSWORD"]

    def get_orders(self, start_date, end_date):
        endpoint = f"{self.BASE_URL}/orders"
        headers = {
            "X-Billbee-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        params = {
            "minOrderDate": start_date.isoformat(),
            "maxOrderDate": end_date.isoformat(),
            "page": 1,
            "pageSize": 250  # Maximale Seitengröße
        }
        
        all_orders = []
        while True:
            try:
                st.info(f"Anfrage an Billbee API: Seite {params['page']}")
                response = requests.get(endpoint, headers=headers, params=params, auth=(self.username, self.password))
                response.raise_for_status()
                data = response.json()
                all_orders.extend(data['Data'])
                
                st.info(f"Erhaltene Bestellungen auf dieser Seite: {len(data['Data'])}")
                
                if len(data['Data']) < params['pageSize']:
                    break
                
                params['page'] += 1
            except requests.RequestException as e:
                st.error(f"Fehler bei der Anfrage an Billbee API: {str(e)}")
                if hasattr(e.response, 'text'):
                    st.error(f"API-Antwort: {e.response.text}")
                raise
        
        st.info(f"Gesamtanzahl der abgerufenen Bestellungen: {len(all_orders)}")
        return all_orders

    def get_orders_for_last_30_days(self):
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        return self.get_orders(start_date, end_date)

billbee_api = BillbeeAPI()
