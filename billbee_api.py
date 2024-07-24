import requests
from datetime import datetime, timedelta
import streamlit as st

class BillbeeAPI:
    BASE_URL = "https://api.billbee.io/api/v1"

    def __init__(self):
        self.api_key = st.secrets["billbee"]["API_KEY"]
        self.username = st.secrets["billbee"]["USERNAME"]
        self.password = st.secrets["billbee"]["PASSWORD"]

    def get_orders_for_date_range(self, start_date, end_date):
        endpoint = f"{self.BASE_URL}/orders"
        headers = {
            "X-Billbee-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        params = {
            "minOrderDate": start_date.isoformat(),
            "maxOrderDate": (end_date + timedelta(days=1)).isoformat(),
            "pageSize": 250  # Max page size
        }
        
        all_orders = []
        
        while True:
            try:
                response = requests.get(endpoint, headers=headers, params=params, auth=(self.username, self.password))
                response.raise_for_status()
                data = response.json()
                all_orders.extend(data['Data'])
                
                if len(data['Data']) < params['pageSize']:
                    break
                
                params['page'] = data['Paging']['Page'] + 1
            except requests.RequestException as e:
                st.error(f"Fehler bei der Anfrage an Billbee API: {str(e)}")
                break
        
        return all_orders

billbee_api = BillbeeAPI()
