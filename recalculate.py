from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import errors
import os

from utils import get_previous_nyt_mini_timestamp

if not os.getenv('GITHUB_ACTIONS'):
    # Code is running locally
    from dotenv import load_dotenv
    load_dotenv()


def recalculate_winners() -> None:
    try:
        uri = os.environ.get('MONGO_URI')

        # Create a new client and connect to the server
        client = MongoClient(uri, server_api=ServerApi('1'))
        db = client.get_database('nyt-mini-times-cluster')
        times = db['times']

        # Retrieve all documents from the 'times' collection and sort by timestamp
        all_documents = list(times.find({}).sort('timestamp', 1))

        # Dictionary to store the winners and their win count
        winners = {}

        # Variables to track the current win streak
        current_winner = None
        current_win_streak = 0
        max_win_streak = 0

        # Filter current day if needed
        prev_mini_timestamp = get_previous_nyt_mini_timestamp()
        if all_documents[-1].get('timestamp').date() > prev_mini_timestamp:
            # Remove the last document from the cursor
            all_documents.pop()

        # Iterate through each document
        for document in all_documents:
            entries = document.get('entries', {})
            timestamp = document.get('timestamp')
            print("===========================")
            print(timestamp)
            print(entries)
            print("===========================")
            # Find the entry with the shortest time
            if entries:
                winner_username = min(entries, key=entries.get)
                # Update the winner's win count
                if winner_username in winners:
                    winners[winner_username] += 1
                else:
                    winners[winner_username] = 1
                # Update the current win streak
                if winner_username == current_winner:
                    current_win_streak += 1
                else:
                    current_winner = winner_username
                    current_win_streak = 1
                # Update the maximum win streak
                max_win_streak = max(max_win_streak, current_win_streak)

        # Print the winners and their win count
        for username, wins in winners.items():
            print(f"Username: {username} | Wins: {wins}")

        # Print the player with the current win streak
        print(f"Player with the current win streak: {current_winner}")
        print(f"Current win streak: {current_win_streak}")

        # Print the maximum win streak
        print(f"Maximum win streak: {max_win_streak}")
    except errors.ConnectionFailure as e:
        raise e
    except errors.OperationFailure as e:
        raise e
    except Exception as e:
        raise
    finally:
        client.close()


def main():

    try:
        recalculate_winners()
    except Exception as e:
        raise e


main()
