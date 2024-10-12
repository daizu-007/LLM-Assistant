import requests

response = requests.post(f"http://localhost:50032/v1/speakers", headers = {"Content-Type": "application/json"}, data={})
print(response.json())