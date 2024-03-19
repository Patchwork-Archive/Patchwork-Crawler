import json
import requests

def check_if_video_valid(api_key: str, videoID: str, min_time=65, max_time=480) -> tuple[bool, str]:
    """
    Check if a video is valid based on its length
    :param api_key: The API key to use for the request
    :param videoID: The ID of the video to check
    :param min_time: The minimum length of the video in seconds
    :param max_time: The maximum length of the video in seconds
    :return: A tuple containing a boolean indicating if the video is valid and the reason if it is not
    """
    url = f"https://holodex.net/api/v2/videos/{videoID}"
    headers = {
        "X-APIKEY": api_key
    }
    api_data = json.loads(requests.get(url, headers=headers).text)
    try:
        if api_data["status"] != "past":
            return False, "Video is not past, its either currently premiering or upcoming"
        if min_time < api_data["duration"] < max_time:
            return True, "Success"
        if api_data["duration"] < min_time:
            return False, f"Video is too short (Less than {min_time} seconds)"
        if api_data["duration"] > max_time:
            return False, f"Video is too long (Exceeds {max_time} seconds)"
    except:
        print(f"An error occurred while trying to check the video {videoID}")
        return False, "An error occurred while trying to check the video"
