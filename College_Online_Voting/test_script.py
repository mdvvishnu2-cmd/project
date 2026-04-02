import requests
import re
from bs4 import BeautifulSoup

BASE_URL = 'http://127.0.0.1:5000'
session = requests.Session()

def test_flow():
    print("Testing index...")
    res = session.get(BASE_URL + '/')
    assert res.status_code == 200
    
    print("Testing admin login...")
    res = session.post(BASE_URL + '/admin/login', data={'username': 'admin', 'password': 'Admin@123'})
    if "Admin Dashboard" not in res.text:
        print(f"FAILED LOGIN: {res.status_code} {res.text}")
    assert "Admin Dashboard" in res.text
    
    print("Testing admin candidates...")
    res = session.get(BASE_URL + '/admin/candidates')
    if res.status_code != 200:
        print(f"FAILED CANDIDATES: {res.status_code} {res.text}")
    assert res.status_code == 200
    
    print("Testing admin logout...")
    res = session.get(BASE_URL + '/admin/logout')
    assert res.status_code == 200
    
    print("Testing voter registration...")
    reg_data = {
        'full_name': 'Test User',
        'email': 'testuser@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890',
        'address': '123 Test St'
    }
    res = session.post(BASE_URL + '/register', data=reg_data)
    assert res.status_code == 200 # Redirects to /login
    
    print("Testing voter login...")
    login_data = {
        'email': 'testuser@example.com',
        'password': 'password123'
    }
    res = session.post(BASE_URL + '/login', data=login_data)
    assert res.status_code == 200 # Redirects to /dashboard
    
    print("Testing voting page...")
    res = session.get(BASE_URL + '/vote')
    assert res.status_code == 200
    
    # Get a candidate ID
    soup = BeautifulSoup(res.text, 'html.parser')
    candidate_card = soup.find('div', class_='candidate-card')
    if candidate_card:
        candidate_id = candidate_card.get('data-id')
        print(f"Testing cast vote for candidate {candidate_id}...")
        res = session.post(BASE_URL + '/vote', data={'candidate_id': candidate_id})
        assert res.status_code == 200 # Redirects to /result
    else:
        print("No candidates found to vote for.")
        
    print("Testing results page...")
    res = session.get(BASE_URL + '/result')
    assert res.status_code == 200
    
    print("Testing voter logout...")
    res = session.get(BASE_URL + '/logout')
    assert res.status_code == 200
    
    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_flow()
