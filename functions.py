#! /usr/bin/python3

#    7-Eleven Python implementation. This program allows you to lock in a fuel price from your computer.
#    Copyright (C) 2019  Freyta
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <https://www.gnu.org/licenses/>.

# Functions used for the TSSA generation
import hmac, base64, hashlib, uuid, time
# Needed for the VmobID
import pyDes
# Functions used for setting our currently locked in fuel prices to the correct timezone
import pytz, datetime
# Used for requests to the price check script and for 7-Eleven stores
import httpx, json
# Functions used for getting the OS environments from settings.py
import settings, os
# Needed for our randomly generated Device ID
import random
# Needed so we can set flask session variables
from flask import session


'''''''''''''''''''''''''''
You can set or change any these environmental variables in settings.py
'''''''''''''''''''''''''''
API_KEY = os.getenv('API_KEY',settings.API_KEY)
TZ = os.getenv('TZ', settings.TZ)
BASE_URL = os.getenv('BASE_URL',settings.BASE_URL)
PRICE_URL = os.getenv('PRICE_URL',settings.PRICE_URL)
DEVICE_NAME = os.getenv('DEVICE_NAME', settings.DEVICE_NAME)
OS_VERSION = os.getenv('OS_VERSION', settings.OS_VERSION)
APP_VERSION = os.getenv('APP_VERSION', settings.APP_VERSION)
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0"

def get_auth_token(email, password, device_id):
    """Gets an authentication token from the 7-Eleven API."""
    url = BASE_URL + "auth/token"
    payload = {
        "client_id": "7eleven-app",
        "grant_type": "password",
        "username": email,
        "password": password,
        "device_id": device_id,
    }
    response = httpx.post(url, json=payload)
    return response.json()


def refresh_auth_token(refresh_token):
    """Refreshes an authentication token from the 7-Eleven API."""
    url = BASE_URL + "auth/token"
    payload = {
        "client_id": "7eleven-app",
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    response = httpx.post(url, json=payload)
    return response.json()

def get_servo_saver_token():
    """Gets a bearer token from the Servo Saver API."""
    url = "https://api.servosavvy.vic.gov.au/v1/auth/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload = {
        "client_id": settings.SERVO_SAVER_CLIENT_ID,
        "client_secret": settings.SERVO_SAVER_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }
    response = httpx.post(url, headers=headers, data=payload)
    return response.json()["access_token"]


def get_fuel_prices():
    """Gets fuel prices from the Servo Saver API."""
    token = get_servo_saver_token()
    headers = {"Authorization": "Bearer " + token}
    response = httpx.get(PRICE_URL, headers=headers)
    return response.json()

def lockedPrices():
    # This function is used for getting our locked in fuel prices to display on the main page

    # Remove all of our previous error messages
    session.pop('ErrorMessage', None)

    headers = {"Authorization": "Bearer " + session["access_token"]}
    response = httpx.get(BASE_URL + "fuel-lock/locks", headers=headers)
    returnContent = json.loads(response.content)

    # An error occours if we have never locked in a price before
    try:
        session['fuelLockId'] = returnContent[0]['Id']
        session['fuelLockStatus'] = returnContent[0]['Status']
        session['fuelLockActive'] = [0,0,0]
        session['fuelLockType'] = returnContent[0]['FuelGradeModel']
        session['fuelLockCPL'] = returnContent[0]['CentsPerLitre']
        session['fuelLockLitres'] = returnContent[0]['TotalLitres']

        tz = pytz.timezone(TZ)

        try:
            ts = returnContent[0]['RedeemedAt']
            session['fuelLockRedeemed'] = datetime.datetime.fromtimestamp(ts).astimezone(tz).strftime('%A %d %B %Y at %I:%M %p')
        except:
            session['fuelLockRedeemed'] = ""

        try:
            ts = returnContent[0]['ExpiresAt']
            session['fuelLockExpiry'] = datetime.datetime.fromtimestamp(ts).astimezone(tz).strftime('%A %d %B %Y at %I:%M %p')
        except:
            pass

        if(session['fuelLockStatus'] == 0):
            session['fuelLockActive'][0] = "Active"

        elif(session['fuelLockStatus'] == 1):
            session['fuelLockActive'][1] = "Expired"

        elif(session['fuelLockStatus'] == 2):
            session['fuelLockActive'][2] = "Redeemed"

        return session['fuelLockId'], session['fuelLockStatus'], session['fuelLockType'], session['fuelLockCPL'], session['fuelLockLitres'], session['fuelLockExpiry'], session['fuelLockRedeemed']

    except:
        # Since we haven't locked in a fuel price before
        session['fuelLockId'] = ""
        session['fuelLockStatus'] = ""
        session['fuelLockActive'] = ""
        session['fuelLockType'] = ""
        session['fuelLockCPL'] = ""
        session['fuelLockLitres'] = ""
        session['fuelLockRedeemed'] = ""
        session['fuelLockExpiry'] = ""

        return session['fuelLockId'], session['fuelLockStatus'], session['fuelLockType'], session['fuelLockCPL'], session['fuelLockLitres'], session['fuelLockExpiry'], session['fuelLockRedeemed']




def getStores():
    # Get a list of all of the stores and their features from the 7-Eleven server.
    # We will use this for our coordinates for a manual lock in
    headers = {"Authorization": "Bearer " + session["access_token"]}
    response = httpx.get(BASE_URL + "store/stores", headers=headers)
    return response.content

def getStoreAddress(storePostcode):
    # Open the stores.json file and read it as a JSON file
    with open('./stores.json', 'r') as f:
        stores = json.load(f)

    # For each store in "Diffs" read the postcode
    for store in stores['Diffs']:
        #print store['PostCode']
        if(store['PostCode'] == storePostcode):
            # Since we have a match, return the latitude + longitude of our store
            return str(store['Latitude']), str(store['Longitude'])

if __name__ == '__main__':
    print("This should be run through app.py")
