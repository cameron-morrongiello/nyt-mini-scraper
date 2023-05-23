from datetime import datetime
import requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import errors
import os

from utils import format_time, get_previous_nyt_mini_timestamp
from stats import get_wins_data, post_pie_charts_to_discord_webhook, post_bar_chart_to_discord_webhook

DAYS_OF_THE_WEEK = ['Monday', 'Tuesday', 'Wednesday',
                    'Thursday', 'Friday', 'Saturday', 'Sunday']

if not os.getenv('GITHUB_ACTIONS'):
    # Code is running locally
    from dotenv import load_dotenv
    load_dotenv()


def update_winners_collection(timestamp) -> tuple:
    """
    Updates the "winners" collection in the MongoDB database with the winner of the NYT Mini puzzle for the given timestamp.

    Args:
        timestamp: datetime object representing the timestamp of the puzzle for which to update the winners collection

    Raises:
        errors.ConnectionFailure: if there is a failure connecting to the MongoDB database
        errors.OperationFailure: if there is an error performing the MongoDB operations

    Returns:
        winners_doc (list): a list of all documents in the "winners" collection sorted by number of wins in descending order
        winner (str): the username of the user with the lowest time in the NYT Mini puzzle for the given timestamp
        existing_doc (dict): the document in the "times" collection for the given timestamp
        existing_doc['weekday'] (str): an integer representing the day of the week (Monday=0, Sunday=6) for the given timestamp
    """
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
    except Exception as e:
        raise e
    finally:
        client.close()


def post_final_standing_to_discord_webhook(all_winners_docs, winner, times_doc, weekday):
    """
    Posts the final standing for the NYT mini puzzle to a Discord webhook.

    Args:
        all_winners_docs (list): A list of dictionaries containing the winner information.
        winner (str): The username of the winner.
        times_doc (dict): A dictionary containing the times information.
        weekday (int): The integer representation of the weekday (0-6).

    Raises:
        requests.exceptions.RequestException: If there is an error in the POST request to the webhook.

    Returns: 
        None
    """
    webhook_url = os.environ.get('DISCORD_WEBHOOK')

    # Sort the times dictionary by the values (i.e., the times)
    sorted_times = dict(
        sorted(times_doc['entries'].items(), key=lambda x: x[1]))

    # Generate the string for the standings
    standing_str = ""
    place = 1
    for username, time in sorted_times.items():
        standing_str += f"{place}. {username} - {format_time(time)}\n"
        place += 1

    # Generate the string for the winners list
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
            'content': f'{winner} won the {DAYS_OF_THE_WEEK[weekday]} Mini and is on a {winners_current_streak} day streak',
            'embeds': [{
                'title': f'Final {DAYS_OF_THE_WEEK[weekday]} Report',
                'description': standing_str
            }]
        }
        # Send the POST request to the webhook URL
        response = requests.post(webhook_url, json=data)
        usernames, wins = get_wins_data()
        post_bar_chart_to_discord_webhook(wins, usernames)
        post_pie_charts_to_discord_webhook()
        # Check the response status code and raise an error if it indicates a failure
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise e
    except Exception as e:
        raise e


def main():
    # Get the timestamp of the previous NYT Mini puzzle
    current_nyt_mini_timestamp = get_previous_nyt_mini_timestamp()
    # Print the timestamp to the console for debugging purposes
    print(f"Previous puzzle: {str(current_nyt_mini_timestamp)}")

    try:
        # Update the winners collection with the latest puzzle times
        all_winners_docs, winner, times_doc, weekday = update_winners_collection(
            current_nyt_mini_timestamp)
        # Post the final standings to a Discord webhook
        post_final_standing_to_discord_webhook(
            all_winners_docs, winner, times_doc, weekday)

    except Exception as e:
        raise e


main()
