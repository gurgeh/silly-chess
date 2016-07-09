import sys

import requests

if __name__ == '__main__':

    requests.post('http://localhost:8080/source',
                  data={'name': 'big', 'fact_type': 'opening'})
    with open(sys.argv[1]) as f:
