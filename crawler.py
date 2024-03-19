from dotenv import load_dotenv
from site_scraper import SiteScraper
import source_parse
import holodex
import os
import time
import requests
import argparse

def log_message(message: str):
    """
    Log a message to the console and a log file
    :param message: The message to log
    """
    current_time_str = time.strftime("%Y-%m-%d %H-%M-%S")
    print(f"{current_time_str}: {message}")

def generate_report(succeeded: list[str], failed: list[tuple[str, str]]):
    """
    Generate a report of the succeeded and failed video IDs
    :param succeeded: A list of succeeded video IDs
    :param failed: A list of failed video IDs
    """
    if not os.path.exists("logs"):
        os.makedirs("logs")
    current_time_str = time.strftime("%Y-%m-%d %H-%M-%S")
    with open(f"logs/report_{current_time_str}.txt", "w") as f:
        f.write("Succeeded:\n")
        for vid in succeeded:
            f.write(f"{vid}\n")
        f.write("\nFailed:\n")
        for vid, reason in failed:
            f.write(f"{vid}: {reason}\n")

def get_content_holodex(api_key: str, start_page: int = 1, end_page: int = 1, min_time: int = 65, max_time: int = 480) -> tuple[list[str], list[tuple[str, str]]]:
    chrome_driver_path = os.getenv("CHROME_DRIVER_PATH")
    if chrome_driver_path is None:
        chrome_driver_path = "/usr/bin/chromedriver"
    scraper = SiteScraper(chrome_driver_path=chrome_driver_path)
    holodex_url = "https://holodex.net/search?q=type,value,text%0Atopic,Music_Cover,Music_Cover%0Atopic,Original_Song,Original_Song&page="
    for page in range(start_page, end_page + 1):
        log_message(f"Getting content via Holodex page {page} of {end_page}")
        data = scraper.get_page_source(f"{holodex_url}{page}")
        video_ids = source_parse.find_all_yt_video_ids(data)
        succeeded = []
        failed = []
        log_message(f"Found {len(video_ids)} videos. Checking validity...")
        for vid in video_ids:
            valid, reason = holodex.check_if_video_valid(api_key, vid, min_time, max_time)
            if valid:
                log_message(f"Video {vid} is valid")
                succeeded.append(vid)
            else:
                log_message(f"Video {vid} is not valid: {reason}")
                failed.append((vid, reason))
    scraper.close()
    return succeeded, failed

def enqueue_content_to_api(videoId: str, prepend_url="https://youtube.com/watch?v=") -> int:
    log_message("Enqueuing content to the API...")
    queue_api = os.getenv("PATCHWORK_API")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'X-AUTHENTICATION': os.getenv("WORKER_AUTH")
    }
    data = {
        'url': prepend_url+videoId,
        'mode': 0
    }
    response = requests.post(queue_api, headers=headers, data=data)
    if response.status_code == 200:
        log_message(f"Successfully enqueued video {videoId}")
    return response.status_code



def main(args):
    valid_video_ids, invalid_video_ids = get_content_holodex(os.getenv("HOLODEX_API_KEY"),
                                                             args.start_page,
                                                             args.end_page,
                                                             args.min_time,
                                                             args.max_time)
    for vid_id in valid_video_ids:
        enqueue_content_to_api(vid_id)
    generate_report(valid_video_ids, invalid_video_ids)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="crawler.py", description="A script to crawl for content. Designed for Patchwork Archive")
    parser.add_argument("--start-page", type=int, default=1, help="The page to start scraping from")
    parser.add_argument("--end-page", type=int, default=1, help="The page to stop scraping at")
    parser.add_argument("--min-time", type=int, default=65, help="The minimum length of a video in seconds")
    parser.add_argument("--max-time", type=int, default=480, help="The maximum length of a video in seconds")
    if not load_dotenv():
        print("No .env file found. Please create one and try again. (Use the template)")
        quit()
    main(args=parser.parse_args())
