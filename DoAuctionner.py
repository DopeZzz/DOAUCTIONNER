import json
import requests
from bs4 import BeautifulSoup
import getpass
from prettytable import PrettyTable
import time

def fancy_print():
    ascii_art = """
"""
    print(ascii_art)

def get_user_input():
    fancy_print()
    username = input("Enter your username: ")
    password = getpass.getpass("Enter your password: ")
    password_asterisks = '*' * len(password)
    print(f"Password: {password_asterisks}")
    return username, password

def obtain_sid(username, password):
    session = requests.Session()
    url = "https://darkorbit.com"
    response = session.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    login_form = soup.find("form", {"name": "bgcdw_login_form"})
    action_url = login_form.get("action")
    payload = {
        "username": username,
        "password": password
    }
    login_response = session.post(action_url, data=payload)
    cookie_dosid = login_response.cookies.get("dosid")
    reload_token = soup.find(name="input", attrs={"name": "reloadToken"})

    if reload_token:
        reload_token_value = reload_token.get("value")
    else:
        print("Element 'reloadToken' not found")
        reload_token_value = None

    sid = None
    if cookie_dosid:
        sid = cookie_dosid
    current_url = login_response.url
    server = current_url.split("//")[1].split(".")[0]
    
    return sid, server, session, reload_token_value

def extract_auction_data_from_source(source_code):
    soup = BeautifulSoup(source_code, 'html.parser')
    items = []
    item_rows = soup.find_all(class_="auctionItemRow")
    auctionbb = soup.find('input', {'name': 'auction_buy_button'}).get('value')

    for idx, row in enumerate(item_rows):
        columns = row.find_all('td')
        item_name = columns[1].text
        highest_bidder = columns[3].text
        current_bid = columns[4].text
        your_bid = columns[5].text

        loot_id_input = row.find("input", id=lambda x: x and x.endswith("_lootId"))
        loot_id = loot_id_input["value"] if loot_id_input else None

        item = {
            "index": idx + 1, 
            "name": item_name.strip(),
            "highest_bidder": highest_bidder.strip(),
            "current_bid": current_bid.strip(),
            "your_bid": your_bid.strip(),
            "loot_id": loot_id
        }
        items.append(item)

    countdowns = soup.find_all(class_="countdown_item")
    time_left = {countdown.get('id').replace("countdown_", ""): countdown.text.strip() for countdown in countdowns}
    return {
        "items": items,
        "time_left": time_left,
        "auction_buy_button": auctionbb 
    }

def get_auction_data(session, category, server):
    url = f"https://{server}.darkorbit.com/ajax/auction.php"
    data = {
        "command": "getAuctionList",
        "category": category,
        "list": "current"
    }

    response = session.post(url, data=data)
    data = json.loads(response.text)

    html_content = data.get('code', '')
    soup = BeautifulSoup(html_content, 'html.parser')

    items = []
    item_rows = soup.find_all(class_="auctionItemRow")
    auctionbb_element = soup.find('input', {'name': 'auction_buy_button'})
    auctionbb = auctionbb_element.get('value', None) if auctionbb_element else None

    for idx, row in enumerate(item_rows):
        item = {}
        item['index'] = idx + 1
        item['name'] = row.find('td', class_='auction_item_name_col').text.strip()
        item['highest_bidder'] = row.find('td', class_='auction_item_highest').text.strip()
        item['current_bid'] = row.find('td', class_='auction_item_current').text.strip()
        item['your_bid'] = '-'
        loot_id_input = row.find("input", id=lambda x: x and x.endswith("_lootId"))
        item['loot_id'] = loot_id_input["value"] if loot_id_input else None
        
        items.append(item)

    countdowns = soup.find_all(class_="countdown_item")
    time_left = {countdown.get('id').replace("countdown_", ""): countdown.text.strip() for countdown in countdowns}

    return {
        "items": items,
        "time_left": time_left,
        "auction_buy_button": auctionbb 
    }

def display_table(data):
    table = PrettyTable()
    table.field_names = ["Number", "Item Name", "Top Bidder", "Bid", "Your Bid", "Loot ID"]

    for item in data["items"]:
        table.add_row([item["index"], item["name"], item["highest_bidder"], item["current_bid"], item["your_bid"], item["loot_id"]])

    print(table)

def get_user_bids(auction_data):
    bids = []

    bid_numbers = input("Enter the item numbers to bid on separated by commas (e.g., 1,2,3): ")
    bid_numbers = list(map(int, bid_numbers.split(',')))

    for num in bid_numbers:
        amount = input(f"Enter the bid amount for item {num}: ")
        bids.append({
            "item": auction_data["items"][num-1],
            "amount": amount
        })

    delay = int(input("Delay in seconds: ")) 

    return bids, delay 



def place_bid(session, server, bids, delay, auctionType):
    for bid in bids:
        auction_url = f"https://{server}.darkorbit.com/indexInternal.es?action=internalAuction"
        response = session.get(auction_url)
        soup = BeautifulSoup(response.text, "html.parser")
        auction_data = extract_auction_data_from_source(response.text)
        reload_token_tag = soup.find(name="input", attrs={"name": "reloadToken"})
        
        if not reload_token_tag:
            print("Error: reloadToken tag not found. Stopping bidding.")
            return
        
        reload_token_value = reload_token_tag['value']

        bid_url = f"https://{server}.darkorbit.com/indexInternal.es?action=internalAuction&reloadToken=" + reload_token_value
        data = {
            "reloadToken": reload_token_value,
            "auctionType": auctionType,
            "subAction": "bid",
            "lootId": bid["item"]["loot_id"],
            "itemId": f"item_{auctionType}_{bid['item']['index']}", 
            "credits": bid["amount"],
            "auction_buy_button": auction_data.get("auction_buy_button")
        }
        
        bid_response = session.post(bid_url, data=data)
        time.sleep(delay)

        if bid_response.status_code == 200:
            print("Request made successfully!")
            #print(reload_token_value)
        else:
            print(f"Error {bid_response.status_code}: {bid_response.text}")

def main():
    username, password = get_user_input()
    sid, server, session, reload_token_value = obtain_sid(username, password)  
    print(f"SID: {sid}")
    option = input("Which auction do you want to bet on? (1. Hour, 2. Day, 3. Week): ")

    if option == "1":
        category = "hour"
        auction_url = f"https://{server}.darkorbit.com/indexInternal.es?action=internalAuction"
        response = session.get(auction_url)
        auction_data = extract_auction_data_from_source(response.text)
    elif option == "2":
        category = "day"
        auction_data = get_auction_data(session, category, server) 
    elif option == "3":
        category = "week"
        auction_data = get_auction_data(session, category, server) 
    else:
        print("Wrong option. You need to select numers 1,2 or 3")
        return

    print(f"Tabla de '{category}':")
    display_table(auction_data)

    user_bids, delay = get_user_bids(auction_data) 
    place_bid(session, server, user_bids, delay, category) 
   
    
    input("Press any key and then 'Enter' to close...")

if __name__ == "__main__":
    main()
