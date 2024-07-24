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
            "pageSize": 100,
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
                if response.status_code != 200:
                    st.error(f"API-Antwort: {response.text}")
                break
        
        st.info(f"Gesamtanzahl der abgerufenen Bestellungen: {len(all_orders)}")
        return all_orders

billbee_api = BillbeeAPI()
