# this program is always running
# update our database every 5 minutes with most recent prices
from bittrex_api_driver import Bittrex
import os
import time
from dotenv import load_dotenv

# plotting
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import matplotlib.cbook as cbook
from matplotlib.ticker import FormatStrFormatter

# for connecting to postgres
import psycopg2

# manages our database
class Postgres:
    def __init__(self, username, password, host, port):
        self.username = username
        self.password = password
        self.host = host
        self.port = port

        # the db we will be using to test our updates
        self.test_db_name = 'testdb_5min'

# manages calls to and from bittrex server, putting them into postgres
class Driver:
    # bittrex is the bittrex api driver for getting prices
    # takes in the bittrex object, postgres object, list of coins, time of updates
    def __init__(self, bittrex, postgres, list, time):
        self.all_coins = list
        self.num_mins = time
        self.bittrex = bittrex
        self.postgres = postgres

        # holds unique id for each coin
        self.coin_id = {}
        # self.create_coin_dict()

    # create the tables we want in our database
    def create_tables(self):
        # drop the tables, not sure if we want this to stay, could be dangerous
        self.drop_tables()

        # establish connection to postgres
        conn = psycopg2.connect(
            database=self.postgres.test_db_name,
            user=self.postgres.username,
            password=self.postgres.password,
            host=self.postgres.host,
            port= self.postgres.port)

        cursor = conn.cursor()

        # we want a coins table to hold our coins ids
        sql = '''CREATE TABLE coins(
        coin_id SERIAL PRIMARY KEY,
        coin_name CHAR(20) NOT NULL
        )'''
        cursor.execute(sql)
        # data = cursor.fetchone()
        # print("Got data: ",data)

        # we want a price table to hold our prices
        sql = '''CREATE TABLE prices(
        p_id VARCHAR PRIMARY KEY,
        coin_id INT NOT NULL,
        price FLOAT NOT NULL,
        volume FLOAT NOT NULL,
        time_secs INT NOT NULL,
        date VARCHAR NOT NULL
        )'''
        cursor.execute(sql)
        conn.commit()
        print("Tables created successfully")
        conn.close()

    def drop_tables(self):
        conn = psycopg2.connect(
            database=self.postgres.test_db_name,
            user=self.postgres.username,
            password=self.postgres.password,
            host=self.postgres.host,
            port= self.postgres.port)

        cursor = conn.cursor()

        # drop coins table
        cursor.execute("DROP TABLE IF EXISTS coins")
        cursor.execute("DROP TABLE IF EXISTS prices")

        # clear our dictionary of coins whose ids we know
        self.coin_id = {}

        conn.commit()
        conn.close()

    # take all coins and assign them a coin_id
    def create_coin_dict(self):
        # first thing we want to do is get the existing coins off the database

        # establish connection to postgres
        conn = psycopg2.connect(
            database=self.postgres.test_db_name,
            user=self.postgres.username,
            password=self.postgres.password,
            host=self.postgres.host,
            port= self.postgres.port)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM coins")

        # get each elt already in coins and add it to our coin id dictionary
        for record in cursor:
            print("got record: ", record)
            self.coin_id[record[1].strip()] = record[0]

        # any coins not already in the database will be assigned an id
        for coin in self.all_coins:
            if coin not in self.coin_id:
                cursor.execute("INSERT INTO coins(coin_name) VALUES(%s) RETURNING coin_id",(coin,))

                # grab the new coin_id
                coin_id = cursor.fetchone()[0]

                # add it to our dict
                self.coin_id[coin] = coin_id

                print("Added coin %s with id %s to dictionary"%(coin,coin_id))
        conn.commit()
        conn.close()


    # add coin to list of coins we are checking
    def add_coin(self, coin):
        # ensure this coin exists
        status, _ = bittrex.get_price(coin)
        if status != 200:
            print("Bittrex error: could not add coin: " + coin + ", status code: " + str(status))
            return

        # ensure this coin is not already in our list of coins
        for coin_name in self.all_coins:
            if coin_name == coin:
                print("Coin %s is already being tracked" % coin_name)
                return
        self.all_coins.append(coin)

        # add this coin to our dictionary and postgres
        self.create_coin_dict()


    def get_all_prices(self):
        for coin in self.all_coins:
            status, price = bittrex.get_price(coin)
            if status != 200:
                print("Could not get price for " + coin + ", status code " + str(status))
            else:
                print(coin + " price = " + str(price))

    # after creating our tables, we want to initialize our db to hold data from the
    # the last month, with one price point every 5 minutes
    def initialize_price_table(self):
        # open a postgres connection
        conn = psycopg2.connect(
            database=self.postgres.test_db_name,
            user=self.postgres.username,
            password=self.postgres.password,
            host=self.postgres.host,
            port= self.postgres.port)
        cursor = conn.cursor()

        # iterate through each coin we track
        for coin_name in self.all_coins:

            # candles are retrieved at intervals of one hour for the last month
            status, candles = bittrex.get_candles(coin_name)
            if status != 200:
                print("Could not get candles for %s" % coin_name)
                continue

            coin_id = self.coin_id[coin_name]
            for candle in candles:
                price = candle['close']
                volume = candle['volume']
                timestamp = candle['startsAt'][:-1]

                parsed_time = time.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
                time_secs = int(time.mktime(parsed_time))

                # we will create our unique key by appending the coin_name to timestamp
                unique_key = str(time_secs) + "-" + coin_name

                # insert this data into postgres
                cursor.execute("INSERT INTO prices(p_id,coin_id,price,volume,time_secs,date) VALUES(%s,%s,%s,%s,%s,%s)",(unique_key,coin_id,price,volume,time_secs,timestamp))
            print("Finished loading prices for %s"%coin_name)
            conn.commit()
        conn.close()

    def plot_coin_graph(self, coin_name):
        coin_id = self.coin_id[coin_name]

        # pull from postgres: prices, timestamps
        # open a postgres connection
        conn = psycopg2.connect(
            database=self.postgres.test_db_name,
            user=self.postgres.username,
            password=self.postgres.password,
            host=self.postgres.host,
            port= self.postgres.port)
        cursor = conn.cursor()

        # lists for holding prices and timestamps
        prices = []
        timestamps = []

        cursor.execute("SELECT price, time_secs FROM prices WHERE coin_id = %s",(coin_id,))
        for record in cursor:
            prices.append(record[0])
            timestamps.append(record[1])

        plt.plot(timestamps,prices)
        plt.title(coin_name)
        plt.xlabel("Timestamp")
        plt.ylabel("Price")
        plt.show()

    def plot_coin_graph_v2(self, coin_name):
        coin_id = self.coin_id[coin_name]

        # pull from postgres: prices, timestamps
        # open a postgres connection
        conn = psycopg2.connect(
            database=self.postgres.test_db_name,
            user=self.postgres.username,
            password=self.postgres.password,
            host=self.postgres.host,
            port= self.postgres.port)
        cursor = conn.cursor()

        # lists for holding prices and timestamps
        prices = []
        timestamps = []

        cursor.execute("SELECT price, time_secs, date FROM prices WHERE coin_id = %s",(coin_id,))
        for record in cursor:
            prices.append(record[0])
            timestamps.append(np.datetime64(record[2]))

        fig, ax = plt.subplots()
        ax.plot(timestamps,prices)
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.format_xdata = mdates.DateFormatter('%m-%d')
        ax.format_ydata = lambda x: f'${x:.2f}'
        ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
        ax.grid(True)
        fig.autofmt_xdate()
        plt.title(coin_name)
        plt.xlabel("Timestamp")
        plt.ylabel("Price")
        plt.show()


if __name__ == '__main__':
    # load our environment variables with our pub and private bittrex keys
    load_dotenv()

    # make sure both env variables are specified or the code will not work
    api_key = os.getenv('bittrex_public')
    secret_key = os.getenv('bittrex_private')

    # make bittrex object
    bittrex = Bittrex(api_key, secret_key)
    # print("mostRecent btc price: " + str(mostRecent))

    postgres_password = os.getenv('postgres_password')
    postgres_username = os.getenv('postgres_username')
    postgres = Postgres(postgres_username,postgres_password,'127.0.0.1','5432')

    # test Driver
    driver = Driver(bittrex, postgres, ['BTC-USD','ETH-USD'], 5)
    driver.add_coin('DOGE-USD')
    driver.get_all_prices()


    driver.create_tables()
    driver.create_coin_dict()
    driver.add_coin('ADA-USD')

    print("\nBeginning candle test:")
    driver.initialize_price_table()
    # driver.create_coin_dict()
    driver.plot_coin_graph_v2('ETH-USD')
    print("coin ids: " + str(driver.coin_id))
