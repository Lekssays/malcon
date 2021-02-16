import json
import urllib3

def check(endpoint: str) -> bool:
    port = endpoint.split(":")
    port = port[1]
    try:
        http = urllib3.PoolManager()
        response = http.request(
            'GET', "http://0.0.0.0:" + port
        )
        if response.status == 200:
            return True
        return False
    except Exception as e:
        print(e)
        return False

def load_endpoints() -> list:
    with open("peers_ports.json", "r") as f:
        peers_ports = json.load(f)

    endpoints = []
    for e in peers_ports:
        endpoints.append(e['peer'] + ":" + str(e['ports']['web']))
    
    return endpoints

def main():
    print("System Health Check")
    endpoints = load_endpoints()
    for endpoint in endpoints:
        peer_id = endpoint.split(":")
        peer_id = peer_id[0]
        if check(endpoint=endpoint):
            print(endpoint + " SUCCESS")
        else:
            print(endpoint + " FAILED")

if __name__ == '__main__':
    main()