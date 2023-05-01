from datetime import datetime, timedelta
import pytz
import requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import errors
import os

from utils import format_time

from dotenv import load_dotenv
load_dotenv()


def get_previous_nyt_mini_timestamp():
    # Set the timezone to Eastern Time
    et_timezone = pytz.timezone('US/Eastern')

    # Get the current time in Eastern Time
    et_time = datetime.now(et_timezone)

    # Check if it's a weekend and the time is past 6 pm ET
    if et_time.weekday() >= 5 and et_time.hour >= 18:
        puzzle_date = et_time.date()
    # Check if it's a weekday and the time is past 10 pm ET
    elif et_time.weekday() < 5 and et_time.hour >= 22:
        puzzle_date = et_time.date()
    else:
        # Otherwise, use the current date minus a day for prev's puzzle
        puzzle_date = et_time.date() - timedelta(days=1)

    return puzzle_date


def update_winners_collection(timestamp):
    try:
        uri = os.environ.get('MONGO_URI')

        # Create a new client and connect to the server
        client = MongoClient(uri, server_api=ServerApi('1'))
        db = client.get_database('nyt-mini-times-cluster')
        times = db['times']
        # Check if a document with the given timestamp already exists
        existing_doc = times.find_one(
            {'timestamp': datetime.fromisoformat(str(timestamp))})
        entries = existing_doc['entries']

        winners = db["winners"]

        # get the lowest user's score from the "entries" dictionary
        winner = min(entries, key=entries.get)

        # increment the winner's score in the collection
        query = {"username": winner}
        update = {"$inc": {"wins": 1}}
        winners.update_one(query, update, upsert=True)

        # increment the winner's win streak by 1
        winners.update_one({"username": winner}, {"$inc": {"win_streak": 1}})

        # set all other users' win streaks to 0
        winners.update_many({"username": {"$ne": winner}},
                            {"$set": {"win_streak": 0}})

        # return the updated documents, winner username, the final times from the day, and the weekday
        res = winners.find().sort(
            "wins", -1)
        winners_doc = []
        for w in res:
            winners_doc.append(w)

        return winners_doc, winner, existing_doc, existing_doc['weekday']

    except errors.ConnectionFailure as e:
        raise e
    except errors.OperationFailure as e:
        raise e
    finally:
        client.close()


def post_final_standing_to_discord_webhook(all_winners_docs, winner, times_doc, weekday):
    webhook_url = os.environ.get('DISCORD_WEBHOOK')
    days_of_week = ['Monday', 'Tuesday', 'Wednesday',
                    'Thursday', 'Friday', 'Saturday', 'Sunday']

    sorted_times = dict(
        sorted(times_doc['entries'].items(), key=lambda x: x[1]))

    standing_str = ""

    place = 1
    for username, time in sorted_times.items():
        standing_str += f"{place}. {username} - {format_time(time)}\n"
        place += 1

    winner_str = ""

    place = 1
    winners_current_streak = 1
    for winners_doc in all_winners_docs:
        if winners_doc['username'] == winner:
            winners_current_streak = winners_doc['win_streak']
        winner_str += f"{place}. {winners_doc['username']} - {winners_doc['wins']} wins\n"
        place += 1

    try:
        # Prepare the data to be sent to the webhook
        data = {
            'content': f'{winner} won the {days_of_week[weekday]} Mini and is on a {winners_current_streak} day streak',
            'embeds': [{
                'title': f'Final {days_of_week[weekday]} Report',
                'description': standing_str
            }, {
                'title': f'Overall Report',
                'description': winner_str
            }]
        }
        # Send the POST request to the webhook URL
        response = requests.post(webhook_url, json=data)

        # Check the response status code and raise an error if it indicates a failure
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise e


def main():
    current_nyt_mini_timestamp = get_previous_nyt_mini_timestamp()
    print(get_previous_nyt_mini_timestamp())
    try:
        all_winners_docs, winner, times_doc, weekday = update_winners_collection(
            current_nyt_mini_timestamp)
        post_final_standing_to_discord_webhook(
            all_winners_docs, winner, times_doc, weekday)

    except Exception as e:
        raise e


main()
