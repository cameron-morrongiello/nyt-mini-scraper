from datetime import datetime, timedelta
import pytz
import requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import errors
import os

from dotenv import load_dotenv
load_dotenv()


def get_current_nyt_mini_timestamp():
   # Set the timezone to Eastern Time
    et_timezone = pytz.timezone('US/Eastern')

    # Get the current time in Eastern Time
    et_time = datetime.now(et_timezone)

    # Check if it's a weekend and the time is past 6 pm ET
    if et_time.weekday() >= 5 and et_time.hour >= 18:
        # If it is, add one day to get the date for the next day's puzzle
        puzzle_date = et_time.date() + timedelta(days=1)
    # Check if it's a weekday and the time is past 10 pm ET
    elif et_time.weekday() < 5 and et_time.hour >= 22:
        # If it is, add one day to get the date for the next day's puzzle
        puzzle_date = et_time.date() + timedelta(days=1)
    else:
        # Otherwise, use the current date for today's puzzle
        puzzle_date = et_time.date()
    return puzzle_date


def get_current_times_doc(timestamp):
    try:
        uri = os.environ.get('MONGO_URI')

        # Create a new client and connect to the server
        client = MongoClient(uri, server_api=ServerApi('1'))
        db = client.get_database('nyt-mini-times-cluster')
        times = db['times']
        # Check if a document with the given timestamp already exists
        existing_doc = times.find_one(
            {'timestamp': datetime.fromisoformat(str(timestamp))})

        return existing_doc

    except errors.ConnectionFailure as e:
        raise e
    except errors.OperationFailure as e:
        raise e
    finally:
        client.close()


def post_final_standing_to_discord_webhook(times_doc):
    webhook_url = os.environ.get('DISCORD_WEBHOOK')
    days_of_week = ['Monday', 'Tuesday', 'Wednesday',
                    'Thursday', 'Friday', 'Saturday', 'Sunday']
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
                'title': f'Current {days_of_week[times_doc["weekday"]]} Standing',
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
    current_nyt_mini_timestamp = get_current_nyt_mini_timestamp()
    print(get_current_nyt_mini_timestamp())
    try:
        times_doc = get_current_times_doc(current_nyt_mini_timestamp)
        print(times_doc)
        if times_doc:
            # post_final_standing_to_discord_webhook(times_doc)
            print("Hi")

    except Exception as e:
        print(e)


main()
