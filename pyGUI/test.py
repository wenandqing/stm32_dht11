# -*- coding: gbk -*-
import requests
import json

# 本机测试可用 localhost，ESP8266用局域网IP：10.115.93.238
url = "http://10.225.198.238:5000/api/upload"
data = {"device_id": 3, "temperature": 26.3, "humidity": 88.5}

response = requests.post(url, json=data)
print(response.json())