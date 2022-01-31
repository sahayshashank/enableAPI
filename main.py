import jwt as pyjwt
import requests
import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from pprint import pprint

API_ORIGIN = "https://api.tilisy.com"
ASPSP_NAME = ""
ASPSP_COUNTRY = "FI"

def main():
    # Load config.json into project
    file_path = os.path.join(os.path.dirname(os.path.abspath("__file__")), "config.json")
    with open(file_path, "r") as f:
        config = json.load(f)
    iat = int(datetime.now().timestamp())
    jwt_body = {
        "iss": "enablebanking.com",
        "aud": "api.tilisy.com",
        "iat": iat,
        "exp": iat + 3600,
    }
    # using the config values to create the JWT, as described on API documentation page
    jwt = pyjwt.encode(
        jwt_body,
        open(os.path.join(config["keyPath"]), "rb").read(),
        algorithm="RS256",
        headers={"kid": config["applicationId"],},
    )
    # print(jwt)
    
    base_headers = {"Authorization": f"Bearer {jwt}"}
    
     # Getting application information
    application = requests.get(f"{API_ORIGIN}/application", headers=base_headers)
    if application.status_code == 200:
        app = application.json()
        # Uncomment following line to display information about application
        # print("Application details:")
        # pprint(app)
    else:
        print(f"Error {application.status_code}:", application.text)
        
    # getting list of banks
    bankList = requests.get(f"{API_ORIGIN}/aspsps", headers=base_headers)
    if bankList.status_code == 200:
        banks = []
        for bank in bankList.json()["aspsps"]:
            if(bank["name"]) not in banks:
                banks.append(bank["name"])
        print("Available Banks : ")
        print(banks)
        ASPSP_NAME=input("Chose bank : ")
    else:
        print(f"Error {bankList.status_code}:", bankList.text)
    
    # authorization
    body = {
        "access": {
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        },
        "aspsp": {"name": ASPSP_NAME, "country": ASPSP_COUNTRY},
        "state": str(uuid.uuid4()),
        "redirect_url": app["redirect_urls"][0],
        "psu_type": "personal",
    }
    auth = requests.post(f"{API_ORIGIN}/auth", json=body, headers=base_headers)
    if auth.status_code == 200:
        auth_url = auth.json()["url"]
        print(f"To authenticate, please copy and paste this URL into a browser window : {auth_url}")
    else:
        print(f"Error {auth.status_code}:", auth.text)
    
    auth_code = input("Paste here the value of 'code' from the URL you were redirected to: ")
    sess = requests.post(f"{API_ORIGIN}/sessions", json={"code": auth_code}, headers=base_headers)
    if sess.status_code == 200:
        session = sess.json()
        print("New user session has been created.")
        # Uncomment following line to display information about the current session
        # pprint(session)
    else:
        print(f"Error {sess.status_code}:", sess.text)
    
    # running a loop to display information about each and every account
    for account in (session["accounts"]):
        account_uid = account["uid"]
        query = {
                "date_from": (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat(),
            }
        # dictionary to hold all transactions of this particular account
        transactions={}
        transactionList = requests.get(
            f"{API_ORIGIN}/accounts/{account_uid}/transactions",
            params=query,
            headers=base_headers,
        )
        if transactionList.status_code == 200:
            resp_data = transactionList.json()
            transactions=(resp_data["transactions"])
        else:
            print(f"Error {transactionList.status_code}:", transactionList.text)
        # Uncomment following line to display all transactions from this account in the last 30 days
        # pprint(transactions)
        maxamt=0.0
        currency = ""
        creditVal=0.0
        debitVal=0.0
        largestTransaction=None
        for t in transactions:
            maxnum = (float(t['transaction_amount']['amount']))
            if maxnum > maxamt:
                maxamt = maxnum
                currency = t['transaction_amount']['currency']
                # storing the entire largest transaction to show details
                largestTransaction = t
            if t['credit_debit_indicator'] == 'CRDT':
            # total credit amount to this account
                creditVal += maxnum
                # total credit value for this account
            if t['credit_debit_indicator'] == 'DBIT':
                # total debit amount from this account
                debitVal += maxnum
        print("\nAccount number : " + account_uid)
        print("Number of transactions in the last 30 days : "+ str(len(transactions)))
        print("Largest transactions value in the last 30 days : "+ str(maxamt) + currency)
        print("Transaction Details : ")
        print(largestTransaction)
        print("Total amount credited : "+ str(creditVal) + currency)
        print("Total amount debited : "+ str(debitVal) + currency)


if __name__ == "__main__":
    main()