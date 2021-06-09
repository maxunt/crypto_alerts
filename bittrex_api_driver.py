# crypto alert bot
# report sharp price changes as well as daily updates via iphone app



# goal of this is simply to set up a bot that will call the bittrex api every 10 minutes
# for a price update on a range of coins and add those numbers to a database
import requests
import time
import hashlib
import hmac


class Bittrex:
    # init with bittrex public and private keys
    def __init__(self, api_key, secret):
        self.api_key = api_key
        self.secret_key = secret

    # return status code, the most recent price of symbol from bittrex
    # creates a GET request to the bittrex api for a symbol to the markets/{symbol}/trades endpoint
    # described here: https://bittrex.github.io/api/v3

    # good resource for understanding the encryption process: https://stackoverflow.com/questions/43559332/python-3-hash-hmac-sha512
    def get_price(self, symbol):
        # endpoint
        url = "https://api.bittrex.com/v3/markets/" + symbol + "/trades"

        # current time in milliseconds
        cTime = int(time.time() * 1000)
        cTime = str(cTime)

        # empty hash value
        hash = hashlib.sha512()
        hash = hash.hexdigest()

        # add all this together and encrypt with secret
        preSign = cTime + url + "GET" + hash

        # encrypt with secret key
        postSign = hmac.new(self.secret_key.encode(), preSign.encode(), hashlib.sha512).hexdigest()

        # json header as specified by bittrex
        header = {
            'Api-Key': self.api_key,
            'Api-Timestamp': cTime,
            'Api-Content-Hash': hash,
            'Api-Signature': postSign,
        }

        # get request to bittrex endpoint
        request = requests.get(url, headers = header)
        if request.status_code != 200:
            return request.status_code, None

        # most recent price is first elt in list
        return request.status_code, request.json()[0]['rate']

    # return candle data for symbol
    def get_candles(self, symbol):
        # endpoint
        url = "https://api.bittrex.com/v3/markets/" + symbol + "/candles/HOUR_1/recent"

        # current time in milliseconds
        cTime = int(time.time() * 1000)
        cTime = str(cTime)

        # empty hash value
        hash = hashlib.sha512()
        hash = hash.hexdigest()

        # add all this together and encrypt with secret
        preSign = cTime + url + "GET" + hash

        # encrypt with secret key
        postSign = hmac.new(self.secret_key.encode(), preSign.encode(), hashlib.sha512).hexdigest()

        # json header as specified by bittrex
        header = {
            'Api-Key': self.api_key,
            'Api-Timestamp': cTime,
            'Api-Content-Hash': hash,
            'Api-Signature': postSign,
        }

        # get request to bittrex endpoint
        request = requests.get(url, headers = header)
        if request.status_code != 200:
            return request.status_code, None

        # most recent price is first elt in list
        return request.status_code, request.json()
