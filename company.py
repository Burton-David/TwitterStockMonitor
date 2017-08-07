import string
import urllib.request
import urllib.error
import json
import bisect

from datetime import datetime, date
from pinance import Pinance
from main import logging

# File path to the list of companies
COMPANIES = './Files/companies.txt'

# File path to the companies being monitored
MONITOR = './Files/monitor.json'


def check_for_companies(tweet, handle):
    """Checks list of companies within the Handle's tweet
       seeing if any companies are listed in their tweet.
       Inputs matches into monitor.json and returns the matches"""

    matches = []

    # Removes punctuation from the tweet
    translator = str.maketrans('', '', string.punctuation)
    edited_tweet = tweet.translate(translator).lower()

    with open(COMPANIES) as f:
        companies = [line.strip() for line in f]

    for word in edited_tweet.split():
        if word == bisect.bisect(word, companies):
            matches.append(word)

    company_dict = get_company_dict()

    comp_d = {}

    # Information that is needed by get_initial/current
    # Fix error: If a company is mentioned that is already in the json, it overwrites it.
    for company in matches:
        comp_d[company] = {}
        comp_d[company]["dateMentioned"] = "{:%d-%m-%Y %H:%M:%S}".format(datetime.now())
        comp_d[company]["handle"] = handle
        comp_d[company]["tweet"] = tweet
        comp_d[company]["day"] = 0
        comp_d[company]["symbol"] = "unknown"
        comp_d[company]["shareChange"] = 0
        comp_d[company]["initialSharePrice"] = 1
        comp_d[company]["currentSharePrice"] = 1
        comp_d[company]["sharePriceList"] = {"0": [], "1": [], "2": [], "3": [],
                                             "4": [], "5": [], "6": [], "7": []}

    company_dict.update(comp_d)
    with open(MONITOR, "w") as f:
        json.dump(company_dict, f, sort_keys=True, indent=4, ensure_ascii=False)

    return matches


def get_initial_company_info():
    """Gets the initial information for each company"""

    company_dict = get_company_dict()

    for company in company_dict:
        # Gets symbol for company
        if company_dict[company]["symbol"] == "unknown":
            try:
                with urllib.request.urlopen(
                      f'https://finance.yahoo.com/_finance_doubledown/'
                      f'api/resource/searchassist;searchTerm={company}') as response:

                    html = response.read().decode()
                    d = json.loads(html)

                    company_dict[company]["symbol"] = d['items'][0]['symbol']

            except urllib.error.HTTPError as error:
                logging.log(error)

        # Gets initial share price
        if company_dict[company]["initialSharePrice"] == 1:
            stock = Pinance(company_dict[company]["Symbol"])
            stock.get_quotes()

            share = stock.quotes_data["LastTradePrice"]

            company_dict[company]["initialSharePrice"] = float(share)
            company_dict[company]["currentSharePrice"] = float(share)

    with open(MONITOR, "w") as f:
        json.dump(company_dict, f, sort_keys=True, indent=4, ensure_ascii=False)


def get_current_shares():
    """Gets current shares, writes updated version back to json"""

    company_dict = get_company_dict()

    for company in company_dict:
        try:
            stock = Pinance(company_dict[company]["symbol"])
            stock.get_quotes()

            share = stock.quotes_data["LastTradePrice"]

            # Gets the current shareprice, replaces the "current"
            # and adds to the sharePriceList
            curr_day = str(company_dict[company]["Day"])
            company_dict[company]["currentSharePrice"] = float(share)
            company_dict[company]["sharePriceList"][curr_day].append(float(share))

            # Gets the current share change
            share_change = 1.0 - (company_dict[company]["Initial-share-price"] /
                                  company_dict[company]["Current-share-price"])
            company_dict[company]["shareChange"] = share_change

        except TypeError as error:
            # Will catch the error if share returns a value other than a float
            logging.log(error)

    with open(MONITOR, "w") as f:
        json.dump(company_dict, f, sort_keys=True, indent=4, ensure_ascii=False)


def get_company_dict():
    """Opens and returns the monitor.json file"""
    with open(MONITOR, 'r') as f:
        return json.load(f)


def current_day():
    """Compares the current date, to the date the tweet was mentioned.
       If it's different to the current "Day" in the json file, replaces it."""

    company_dict = get_company_dict()

    remove = []  # Keeps a list of companies that have reached their 7 day limit, and removes them

    # Create a date object with the current time
    current_date = datetime.now()
    d1 = date(current_date.year, current_date.month, current_date.day)

    for company in company_dict:
        date_mentioned = company_dict[company]["Date-mentioned"]

        # Converts "04-08-2017 22:34:49", to [2017, 08, 04]
        date_mentioned = date_mentioned.split()[0]
        date_mentioned = date_mentioned.split("-")[::-1]

        # Create second date object with the "Date-mentioned" time to compare to d1
        d0 = date(int(date_mentioned[0]), int(date_mentioned[1]), int(date_mentioned[2]))
        day = abs((d1 - d0).days)

        if day > 7:
            remove.append(company)

        else:
            company_dict[company]["Day"] = day

    for company in remove:
        # Add something here to keep track of the older mentions
        del company_dict[company]

    with open(MONITOR, "w") as f:
        json.dump(company_dict, f, sort_keys=True, indent=4, ensure_ascii=False)