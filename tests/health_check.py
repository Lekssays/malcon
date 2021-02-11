import argparse
import urllib3

def parse_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-o', '--orgs',
                        dest = "orgs",
                        help = "Orgs Number",
                        default = 3,
                        required = True)
    parser.add_argument('-p', '--peers',
                        dest = "peers",
                        help = "Number of Peers per Org",
                        default = 2,
                        required = True)
    return parser.parse_args()

def check(endpoint: str) -> bool:
    try:
        http = urllib3.PoolManager()
        response = http.request(
            'GET', endpoint
        )
        if response.status == 200:
            return True
        return False
    except Exception as e:
        return False

def main():
    print("System Health Check")
    orgs = int(parse_args().orgs)
    peers = int(parse_args().peers)

    for org in range(1, orgs + 1):
        for peer in range(0, peers):
            peer_id = "peer{}.org{}.example.com".format(str(peer), str(org))
            endpoint = "http://0.0.0.0:100{}{}".format(str(org), str(peer))
            if check(endpoint):
                print(peer_id + " SUCCESS")
            else:
                print(peer_id + " FAILED")

if __name__ == '__main__':
    main()