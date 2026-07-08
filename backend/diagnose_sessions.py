import requests, sys, os

BASE = os.environ.get('BASE_URL','http://127.0.0.1:8000')

url = BASE + '/api/v1/sessions/?classe=20'
print('GET', url)

try:
    r = requests.get(url, timeout=30)
    print('status', r.status_code)
    print('body', r.text[:2000])
except Exception as e:
    print('request failed', repr(e))
    sys.exit(1)

