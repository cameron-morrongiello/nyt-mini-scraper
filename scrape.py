from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup as soup
import calendar
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import errors
import os

from utils import format_time

if not os.getenv('GITHUB_ACTIONS'):
    # Code is running locally
    from dotenv import load_dotenv
    load_dotenv()

DAYS_OF_THE_WEEK = ['Monday', 'Tuesday', 'Wednesday',
                    'Thursday', 'Friday', 'Saturday', 'Sunday']

# Modified from: https://github.com/pjflanagan/nyt-crossword-plus/blob/main/scrape/main.py


def get_cookie(username: str, password: str) -> str:
    """
    Log into a service and return the value of the 'NYT-S' cookie.

    Args:
        username (str): The username to use for authentication.
        password (str): The password to use for authentication.

    Raises:
        ValueError: If the 'NYT-S' cookie is not found.

    Returns:
        str: The value of the 'NYT-S' cookie.
    """

    # Send a POST request with login credentials to authenticate.
    login_resp = requests.post(
        'https://myaccount.nytimes.com/svc/ios/v2/login',
        data={
            'login': username,
            'password': password,
        },
        headers={
            'User-Agent': 'Crosswords/20191213190708 CFNetwork/1128.0.1 Darwin/19.6.0',
            'client_id': 'ios.crosswords',
        }
    )

    # Raise an exception if there was an error with authentication.
    login_resp.raise_for_status()

    # Find the 'NYT-S' cookie and return its value.
    for cookie in login_resp.json()['data']['cookies']:
        if cookie['name'] == 'NYT-S':
            return cookie['cipheredValue']

    # Raise an exception if the 'NYT-S' cookie was not found.
    raise ValueError('NYT-S cookie not found')

# Modified from: https://github.com/pjflanagan/nyt-crossword-plus/blob/main/scrape/main.py


def scrape_leaderboard(cookie: str) -> tuple:
    """
    Scrapes the leaderboard for the NYT crossword puzzle and returns a tuple
    containing the date, weekday, and a dictionary of usernames and completion
    times in seconds.

    Args:
        cookie (str): NYT-S cookie needed to access the leaderboard.

    Returns:
        tuple: A tuple containing the date, weekday, and a dictionary of usernames
        and completion times in seconds.
    """

    # Request the leaderboard page with the NYT-S cookie
    url = 'https://www.nytimes.com/puzzles/leaderboards'
    response = requests.get(url, cookies={'NYT-S': cookie})

    # Parse the page with BeautifulSoup
    page = soup(response.content, features='html.parser')

    # Extract the date from the page
    solvers = page.find_all('div', class_='lbd-score')
    [_, month, day, year] = page.find(
        'h3', class_='lbd-type__date').text.strip().split()

    # Format the date and get the weekday
    day = day.replace(",", "")
    month_number = list(calendar.month_name).index(month)
    month_string = f'{month_number:02d}'
    day_string = f'{int(day):02d}'
    timestamp = year + '-' + month_string + '-' + day_string
    weekday = calendar.weekday(int(year), int(month_number), int(day))

    # Extract the completion times and usernames
    entries = {}
    for solver in solvers:
        name = solver.find('p', class_='lbd-score__name').text.strip()
        try:
            parsed_time = solver.find(
                'p', class_='lbd-score__time').text.strip()

            if parsed_time != '--':
                minutes, seconds = parsed_time.split(':')
                time = (60 * int(minutes)) + int(seconds)

                if name.endswith('(you)'):
                    name = name.replace('(you)', '').strip()

                entries.update({name: time})
        except:
            # Ignore any solvers without completion times
            pass

    # Return the date, weekday, and completion times dictionary
    return datetime.fromisoformat(timestamp), weekday, entries


def enter_times_in_db(timestamp, weekday, entries) -> tuple:
    """
    Inserts or updates a document with the given timestamp and entries in the MongoDB collection.

    Args:
        timestamp (str): The timestamp of the document in ISO format (YYYY-MM-DD).
        weekday (int): The weekday index of the timestamp (0=Monday, 6=Sunday).
        entries (dict): A dictionary mapping usernames to completion times in seconds.

    Raises:
        ConnectionFailure: If there is failed connection to the database
        OperationFailure: If there is a operation failed when read/write 

    Returns:
        tuple: A tuple containing the document object and a dictionary of new entries added, if any.
    """
    try:
        uri = os.environ.get('MONGO_URI')

        # Create a new client and connect to the server
        client = MongoClient(uri, server_api=ServerApi('1'))
        db = client.get_database('nyt-mini-times-cluster')
        times = db['times']

        # Check if a document with the given timestamp already exists
        existing_doc = times.find_one({'timestamp': timestamp})

        if existing_doc is None:
            # Create a new document with all the passed-in values
            new_doc = {
                'weekday': weekday,
                'timestamp': timestamp,
                'entries': entries
            }
            times.insert_one(new_doc)
            print(f"Inserted new document with entries {entries}")
            return new_doc, entries
        else:
            # Check if the passed-in entries is different from the current entries object in the database
            doc_entries = dict(existing_doc['entries'])
            if entries != doc_entries:
                # Update the entries field with the passed-in entries
                times.update_one({'timestamp': timestamp}, {
                                 '$set': {'entries': entries}})
                print(
                    f"Updated document with timestamp {timestamp} with new entries")
                new_times = {k: v for k, v in entries.items()
                             if k not in doc_entries.keys()}
                # manually update doc to pass along
                existing_doc['entries'] = entries
                return existing_doc, new_times

            else:
                print(
                    f"Document with timestamp {timestamp} already exists and has not been updated")
                return existing_doc, None

    except errors.ConnectionFailure as e:
        raise e
    except errors.OperationFailure as e:
        raise e
    finally:
        client.close()


def post_new_times_to_discord_webhook(new_times):
    """
    Posts new solve times to a Discord webhook.

    Args:
        new_times (dict): A dictionary containing usernames as keys and solve times as values.

    Raises:
        requests.exceptions.RequestException: If the POST request to the webhook URL fails.

    Returns:
        None
    """

    # Retrieve the Discord webhook URL from an environment variable
    webhook_url = os.environ.get('DISCORD_WEBHOOK')

    # Iterate through each user and their corresponding solve time
    for username, time in new_times.items():
        try:
            # Prepare the data to be sent to the webhook
            data = {
                'content': f'{username} completed the Mini in {format_time(time)}',
            }

            # Send the POST request to the webhook URL
            response = requests.post(webhook_url, json=data)

            # Check the response status code and raise an error if it indicates a failure
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise e


def post_current_standing_to_discord_webhook(times_doc):
    """
    Posts the current standing of entries to a Discord webhook.

    Args:
        times_doc (dict): A dictionary containing entries and their times.

    Raises:
        requests.exceptions.RequestException: If the POST request to the webhook URL fails.

    Returns:
        None
    """
    webhook_url = os.environ.get('DISCORD_WEBHOOK')

    # Sort the entries in times_doc by their values
    sorted_times = dict(
        sorted(times_doc['entries'].items(), key=lambda x: x[1]))

    # Format the sorted entries into a string
    description_str = ""
    place = 1
    for username, time in sorted_times.items():
        description_str += f"{place}. {username} - {format_time(time)}\n"
        place += 1

    try:
        # Prepare the data to be sent to the webhook
        data = {
            'embeds': [{
                'title': f'Current {DAYS_OF_THE_WEEK[times_doc["weekday"]]} Standing',
                'description': description_str
            }]
        }
        # Send the POST request to the webhook URL
        response = requests.post(webhook_url, json=data)

        # Check the response status code and raise an error if it indicates a failure
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise e


def main():

    try:
        # Get the NYT username and password from the environment variables
        username = os.environ.get('NYT_USERNAME')
        password = os.environ.get('NYT_PASSWORD')

        # Get a cookie for the NYT leaderboard using the username and password
        cookie = get_cookie(username, password)

        # Scrape the leaderboard for the current timestamp, weekday, and entries
        timestamp, weekday, entries = scrape_leaderboard(cookie)

        if entries:
            print(entries)

            # Enter the entries into the Firestore database and get any new entries
            doc, new_times = enter_times_in_db(timestamp, weekday, entries)
            print(new_times)

            # If there are new entries, post them to Discord
            if new_times:
                post_new_times_to_discord_webhook(new_times)
                post_current_standing_to_discord_webhook(doc)

        # If there are no entries in the leaderboard
        else:
            print("No entries")

    except Exception as e:
        raise e


main()
