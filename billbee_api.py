import requests
from datetime import datetime, timedelta
import streamlit as st

class BillbeeAPI:
    BASE_URL = "https://api.billbee.io/api/v1"

    def __init__(self):
        self.api_key = st.secrets["billbee"]["API_KEY"]
        self.username = st.secrets["billbee"]["USERNAME"]
        self.password = st.secrets["billbee"]["PASSWORD"]

    def get_last_50_orders(self):
        endpoint = f"{self.BASE_URL}/orders"
        headers = {
            "X-Billbee-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        params = {
            "page": 1,
            "pageSize": 50,
            "orderBy": "CreatedAt",
            "orderDirection": "DESC"
        }
        
        try:
            response = requests.get(endpoint, headers=headers, params=params, auth=(self.username, self.password))
            response.raise_for_status()
            return response.json()['Data']
        except requests.RequestException as e:
            st.error(f"Fehler bei der Anfrage an Billbee API: {str(e)}")
            return []

billbee_api = BillbeeAPI()
