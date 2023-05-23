import pytz
from datetime import datetime, timedelta


def format_time(seconds):
    """
    Format time in seconds into a string of the format 'mm:ss'.

    Args:
        seconds: an integer representing the time in seconds

    Returns:
        A string of the format 'mm:ss'
    """
    # Convert seconds into minutes and seconds
    minutes, seconds = divmod(seconds, 60)

    return f"{minutes:02d}:{seconds:02d}"


def get_previous_nyt_mini_timestamp() -> datetime.date:
    """
    Calculates the timestamp of the previous New York Times Mini puzzle.

    Returns:
        puzzle_date (datetime.date): A date object representing the date of the previous
            New York Times Mini puzzle.
    """
    # Set the timezone to Eastern Time
    et_timezone = pytz.timezone('US/Eastern')

    # Get the current time in Eastern Time
    et_time = datetime.now(et_timezone)

    # Check if it's a weekend and the time is past 6 pm ET
    # but before midnight
    if et_time.weekday() >= 5 and et_time.hour >= 18 and et_time.hour < 24:
        puzzle_date = et_time.date()
    # Check if it's a weekday and the time is past 10 pm ET
    # but before midnight
    elif et_time.weekday() < 5 and et_time.hour >= 22 and et_time.hour < 24:
        puzzle_date = et_time.date()
    else:
        # Otherwise, use the current date minus a day for prev's puzzle
        puzzle_date = et_time.date() - timedelta(days=1)

    return puzzle_date
