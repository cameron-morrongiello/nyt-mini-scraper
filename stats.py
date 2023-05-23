import matplotlib.pyplot as plt
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import errors
import requests
import io
import os

from utils import get_previous_nyt_mini_timestamp

if not os.getenv('GITHUB_ACTIONS'):
    # Code is running locally
    from dotenv import load_dotenv
    load_dotenv()


def post_pie_charts_to_discord_webhook():
    try:
        uri = os.environ.get('MONGO_URI')

        # Create a new client and connect to the server
        client = MongoClient(uri, server_api=ServerApi('1'))
        db = client.get_database('nyt-mini-times-cluster')
        times_collection = db['times']

        # Retrieve the wins data per person per day from the collection
        all_documents = list(times_collection.find())
        weekdays = ['Monday', 'Tuesday', 'Wednesday',
                    'Thursday', 'Friday', 'Saturday', 'Sunday']
        # Prepare data for the pie charts

        # Filter current day if needed
        prev_mini_timestamp = get_previous_nyt_mini_timestamp()
        if all_documents[-1].get('timestamp').date() > prev_mini_timestamp:
            # Remove the last document from the cursor
            all_documents.pop()

        data = {}
        colors = {}
        for document in all_documents:
            weekday = weekdays[document['weekday']]
            entries = document['entries']

            # Calculate the winner for the day based on the shortest time entry
            winner = min(entries, key=entries.get)

            if weekday not in data:
                data[weekday] = {}

            if winner not in data[weekday]:
                data[weekday][winner] = 0

            data[weekday][winner] += 1

            if winner not in colors:
                colors[winner] = plt.cm.Set3(len(colors))

        # Generate the combined pie chart for all weekdays
        # Create a new figure for the combined pie chart
        fig, axs = plt.subplots(2, 4, figsize=(12, 6))

        # Calculate the total number of subplots required
        num_subplots = len(weekdays)

        all_usernames = []
        all_wedges = []

        for i, weekday in enumerate(weekdays):
            # Retrieve the wins data for the current weekday
            wins_data = data.get(weekday, {})

            # Extract the usernames and wins for the current weekday
            usernames = list(wins_data.keys())
            wins = list(wins_data.values())

            # Create a subplot for the current weekday
            ax = axs[i // 4, i % 4]

            # Generate the pie chart for the current weekday
            wedges, _ = ax.pie(wins, labels=wins, labeldistance=0.75, startangle=90, colors=[
                               colors[u] for u in usernames])
            ax.set_title(f'{weekday}')
            ax.axis('equal')  # Equal aspect ratio ensures circular pie chart

            # Get the wedges abd labels that will be used for the overall legend

            for j, username in enumerate(usernames):
                if username not in all_usernames:
                    all_usernames.append(username)
                    all_wedges.append(wedges[j])

       # Remove the extra subplot if there are less than 8 weekdays
        if num_subplots < 8:
            axs[-1, -1].remove()

        # Adjust spacing between subplots
        plt.tight_layout()

        # Create a single legend for all the pie charts
        plt.legend(all_wedges, all_usernames, title='Usernames',
                   loc='center left', bbox_to_anchor=(1, 0.5))

        # Save the combined pie chart image to a BytesIO object
        image_stream = io.BytesIO()
        plt.savefig(image_stream, format='png')
        plt.close()

        # Reset the file pointer of the stream to the beginning
        image_stream.seek(0)

        # Convert the image stream to a Discord-compatible file object
        file_obj = image_stream.getvalue()

        # Create a multipart/form-data payload for sending the file
        files = {
            'file': ('chart.png', file_obj, 'image/png')
        }

        # Post the image to Discord webhook
        webhook_url = os.environ.get('DISCORD_WEBHOOK')
        payload = {
            # 'username': 'Chart Bot',
            # 'content': 'Check out the wins breakdown per weekday!'
        }
        response = requests.post(webhook_url, data=payload, files=files)

        # Check if the request was successful
        if response.status_code == 200:
            print('Combined pie chart image posted to Discord successfully.')
        else:
            print('Failed to post combined pie chart image to Discord.')

    except errors.ConnectionFailure as e:
        raise e
    except errors.OperationFailure as e:
        raise e


def get_wins_data():
    try:
        uri = os.environ.get('MONGO_URI')

        # Create a new client and connect to the server
        client = MongoClient(uri, server_api=ServerApi('1'))
        db = client.get_database('nyt-mini-times-cluster')
        winners_collection = db['winners']

        # Retrieve the username and wins data from the collection
        cursor = winners_collection.find({}, {'username': 1, 'wins': 1})

        # Extract usernames and wins from the cursor
        usernames = []
        wins = []
        for document in cursor:
            usernames.append(document['username'])
            wins.append(document['wins'])

        return usernames, wins

    except errors.ConnectionFailure as e:
        raise e
    except errors.OperationFailure as e:
        raise e
    except Exception as e:
        raise e
    finally:
        client.close()


def post_bar_chart_to_discord_webhook(wins, usernames):
    # Create a bar chart using Matplotlib
    plt.bar(usernames, wins)
    plt.ylabel('Wins')
    plt.title('Mini Crushers Total Wins')

   # Save the chart image to a BytesIO object
    image_stream = io.BytesIO()
    plt.savefig(image_stream, format='png')
    plt.close()

    # Reset the file pointer of the stream to the beginning
    image_stream.seek(0)

    # Convert the image stream to a Discord-compatible file object
    file_obj = image_stream.getvalue()

    # Create a multipart/form-data payload for sending the file
    files = {
        'file': ('chart.png', file_obj, 'image/png')
    }

    # Post the image to Discord webhook
    webhook_url = os.environ.get('DISCORD_WEBHOOK')
    payload = {
        # 'content': 'Overall Report'
    }
    response = requests.post(webhook_url, data=payload, files=files)
    # Check if the request was successful
    if response.status_code == 200:
        print('Chart image posted to Discord successfully.')
    else:
        print('Failed to post chart image to Discord.')


if __name__ == "__main__":
    usernames, wins = get_wins_data()
    post_bar_chart_to_discord_webhook(wins, usernames)
    post_pie_charts_to_discord_webhook()
