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
