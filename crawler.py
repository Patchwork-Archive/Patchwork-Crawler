from dotenv import load_dotenv
from site_scraper import SiteScraper
import source_parse
import holodex
import youtube
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

def generate_report(succeeded: list[str], failed: list[tuple[str, str]]) -> str:
    """
    Generate a report of the succeeded and failed video IDs
    :param succeeded: A list of succeeded video IDs
    :param failed: A list of failed video IDs
    :returns: The path to the report file
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
    return f"logs/report_{current_time_str}.txt"

# def merge_report(report1: str, report2: str, sep_text="") -> str:
#     """
#     Merge two reports into one. Report2 will be appended to the end of Report1
#     :param report1: The path to the first report
#     :param report2: The path to the second report
#     :param sep_text: The text to separate the reports
#     :returns: The path to the merged report
#     """
#     with open(report1, "a") as f1:
#         with open(report2, "r") as f2:
#             f1.write(sep_text)
#             f1.write(f2.read())
#     return report1


def get_content_holodex(api_key: str, start_page: int = 1, end_page: int = 1, min_time: int = 65, max_time: int = 480, wait_time: int =5) -> tuple[list[str], list[tuple[str, str]]]:
    chrome_driver_path = os.getenv("CHROME_DRIVER_PATH")
    if chrome_driver_path is None:
        chrome_driver_path = "/usr/bin/chromedriver"
    scraper = SiteScraper(chrome_driver_path=chrome_driver_path)
    holodex_url = "https://holodex.net/search?q=type,value,text%0Atopic,Music_Cover,Music_Cover%0Atopic,Original_Song,Original_Song&page="
    for page in range(start_page, end_page + 1):
        log_message(f"Getting content via Holodex page {page} of {end_page}")
        data = scraper.get_page_source(f"{holodex_url}{page}", wait_time)
        video_ids = source_parse.find_all_yt_video_ids_hldex(data)
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
    if not args.youtube:
        # Default Holodex mode
        valid_video_ids, invalid_video_ids = get_content_holodex(os.getenv("HOLODEX_API_KEY"),
                                                                args.start_page,
                                                                args.end_page,
                                                                args.min_time,
                                                                args.max_time,
                                                                args.wait_time
                                                                )
        for vid_id in valid_video_ids:
            enqueue_content_to_api(vid_id)
        generate_report(valid_video_ids, invalid_video_ids)
        return
    # YouTube mode
    if args.channel_id_source == "DB":
        pass
    else:
        file = open(args.channel_id_source, "r")
        if not os.path.exists("logs"):
            os.makedirs("logs")
        for line in file:
            channel_id = line.strip()
            succeeded, failed = youtube.get_content_youtube(channel_id)
            succeeded = list(set(succeeded))
            failed = list(set(failed))
            for vid_id, title in succeeded:
                print(f"Validated {vid_id} - {title} to API")
                enqueue_content_to_api(vid_id)
                
            


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="crawler.py", description="A script to crawl for content. Designed for Patchwork Archive")
    parser.add_argument("--start-page", type=int, default=1, help="The page to start scraping from")
    parser.add_argument("--end-page", type=int, default=1, help="The page to stop scraping at")
    parser.add_argument("--min-time", type=int, default=65, help="The minimum length of a video in seconds")
    parser.add_argument("--max-time", type=int, default=480, help="The maximum length of a video in seconds")
    parser.add_argument("--wait_time", type=int, default=5, help="The amount of time to wait for JS to load in sec (default=5)")
    parser.add_argument("--youtube", action="store_true", help="Scrape YouTube channels instead of Holodex")
    parser.add_argument("--channel_id_source", type=str, default="channels.txt", help="The file containing the channel IDs. Specify DB to use MySQL DB via env variables")
    if not load_dotenv():
        print("No .env file found. Please create one and try again. (Use the template)")
        quit()
    main(args=parser.parse_args())
