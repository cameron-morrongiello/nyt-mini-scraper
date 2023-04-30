from datetime import datetime
import requests
from bs4 import BeautifulSoup as soup
import calendar
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import errors
import os

# from dotenv import load_dotenv
# load_dotenv()

DAYS_OF_THE_WEEK = ['Monday', 'Tuesday', 'Wednesday',
                    'Thursday', 'Friday', 'Saturday', 'Sunday']

# Modified from: https://github.com/pjflanagan/nyt-crossword-plus/blob/main/scrape/main.py


def get_cookie(username, password):
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
    login_resp.raise_for_status()
    for cookie in login_resp.json()['data']['cookies']:
        if cookie['name'] == 'NYT-S':
            return cookie['cipheredValue']
    raise ValueError('NYT-S cookie not found')

# Modified from: https://github.com/pjflanagan/nyt-crossword-plus/blob/main/scrape/main.py


def scrape_leaderboard(cookie):
    url = 'https://www.nytimes.com/puzzles/leaderboards'
    response = requests.get(url, cookies={
        'NYT-S': cookie,
    })
    page = soup(response.content, features='html.parser')

    solvers = page.find_all('div', class_='lbd-score')
    [_, month, day, year] = page.find(
        'h3', class_='lbd-type__date').text.strip().split()

    day = day.replace(",", "")
    month_number = list(calendar.month_name).index(month)
    month_string = f'{month_number:02d}'
    day_string = f'{int(day):02d}'
    timestamp = year + '-' + month_string + '-' + day_string

    weekday = calendar.weekday(int(year), int(month_number), int(day))

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

                entries.update({
                    name: time
                })
        except:
            pass

    return datetime.fromisoformat(timestamp), weekday, entries


def enter_times_in_db(timestamp, weekday, entries):
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

    webhook_url = os.environ.get('DISCORD_WEBHOOK')
    for username, time in new_times.items():
        try:
            # Prepare the data to be sent to the webhook
            data = {
                'content': f'{username} completed the Mini in {time}s',
            }

            # Send the POST request to the webhook URL
            response = requests.post(webhook_url, json=data)

            # Check the response status code and raise an error if it indicates a failure
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise e


def post_current_standing_to_discord_webhook(times_doc):
    webhook_url = os.environ.get('DISCORD_WEBHOOK')

    sorted_times = dict(
        sorted(times_doc['entries'].items(), key=lambda x: x[1]))

    description_str = ""

    place = 1
    for username, time in sorted_times.items():
        description_str += f"{place}. {username} - {time}s\n"
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
        username = os.environ.get('NYT_USERNAME')
        password = os.environ.get('NYT_PASSWORD')
        cookie = get_cookie(username, password)
        timestamp, weekday, entries = scrape_leaderboard(cookie)
        if entries:
            print(entries)
            doc, new_times = enter_times_in_db(timestamp, weekday, entries)
            print(new_times)
            if new_times:
                # if there is new times, post it to discord
                post_new_times_to_discord_webhook(new_times)
                post_current_standing_to_discord_webhook(doc)
        else:
            print("No entries")
    except Exception as e:
        print(e)


main()
