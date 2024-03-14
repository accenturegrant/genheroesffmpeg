import requests

url = 'http://localhost:8000/process'
headers = {'Accept' : 'application/json', 'Content-Type' : 'application/json'}
r = requests.post(url, data=open('post.json', 'rb'), headers=headers)
