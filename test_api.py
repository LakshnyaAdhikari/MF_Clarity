import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def wait_for_server():
    for _ in range(10):
        try:
            resp = requests.get(BASE_URL + "/")
            if resp.status_code == 200:
                print("Server is up!")
                return True
        except:
            pass
        print("Waiting for server...")
        time.sleep(2)
    return False

def test_recommendation():
    payload = {
        "amount": 50000,
        "horizon_years": 5,
        "risk_tolerance": "Moderate",
        "goal": "Wealth Creation"
    }
    print(f"Testing /recommend with payload: {payload}")
    resp = requests.post(BASE_URL + "/recommend", json=payload)
    if resp.status_code == 200:
        data = resp.json()
        print("Success! Response:")
        import json
        print(json.dumps(data, indent=2))
        
        # Validation
        alloc = data['allocation']
        assert abs(alloc['Equity'] + alloc['Debt'] - 1.0) < 0.01, "Allocation mismatch"
        assert len(data['portfolio']) > 0, "Portfolio empty"
        print("Validation Passed.")
    else:
        print(f"Failed! Status: {resp.status_code}, Text: {resp.text}")
        sys.exit(1)

if __name__ == "__main__":
    if wait_for_server():
        test_recommendation()
    else:
        print("Server failed to start.")
        sys.exit(1)
