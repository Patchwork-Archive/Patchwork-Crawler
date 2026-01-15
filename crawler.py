from dotenv import load_dotenv
from site_scraper import SiteScraper
from sql_handler import SQLHandler
import source_parse
import holodex
import youtube
import os
import time
import requests
import argparse

# Constant value for a search page to find covers and songs
HOLODEX_SEARCH_PAGE = "https://holodex.net/search?q=type,value,text%0Atopic,Music_Cover,Music_Cover%0Atopic,Original_Song,Original_Song&page="

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

def get_content_holodex(api_key: str, start_page: int = 1, end_page: int = 1, min_time: int = 45, max_time: int = 600, wait_time: int =5) -> tuple[list[str], list[tuple[str, str]]]:
    chrome_driver_path = os.getenv("CHROME_DRIVER_PATH")
    if chrome_driver_path is None:
        chrome_driver_path = "/usr/bin/chromedriver"
    scraper = SiteScraper(chrome_driver_path=chrome_driver_path, wait_time=wait_time)
    succeeded = []
    failed = []
    for page in range(start_page, end_page + 1):
        log_message(f"Getting content via Holodex page {page} of {end_page}")
        data = scraper.get_page_source(f"{HOLODEX_SEARCH_PAGE}{page}")
        video_ids = source_parse.find_all_yt_video_ids_hldex(data)
        log_message(f"Found {len(video_ids)} videos. Checking validity...")
        for vid in video_ids:
            try:
                valid, reason = holodex.check_if_video_valid(api_key, vid, min_time, max_time)
            except:
                log_message(f"An error occurred while trying to check the video {vid}")
                valid = False
                reason = "An error occurred while trying to check the video"
            if valid:
                log_message(f"Video {vid} is valid")
                succeeded.append(vid)
            else:
                log_message(f"Video {vid} is not valid: {reason}")
                failed.append((vid, reason))
    scraper.close()
    return succeeded, failed

def get_content_headless_holodex(start_page: int = 1, end_page: int = 2, min_time: int = 45, max_time: int = 600) ->  tuple[list[str], list[tuple[str, str]]]:
    """
    Directly read from API endpoint
    """
    url = "https://holodex.net/api/v2/search/videoSearch"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/json",
        "Sec-GPC": "1",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Referer": "https://holodex.net/search?q=type,value,text%0Atopic,Music_Cover,Music_Cover"
    }
    succeeded = []
    failed = []
    for page in range(start_page, end_page + 1):
        # Calculate offset - each page has 30 items
        offset = (page - 1) * 30

        log_message(f"Getting content via Holodex API page {page} of {end_page} (offset: {offset})")

        # Request body with proper offset
        body = {
            "sort": "newest",
            "lang": ["en"],
            "target": ["stream", "clip"],
            "conditions": [],
            "topic": ["Music_Cover"],
            "vch": [],
            "org": [],
            "comment": [],
            "paginated": True,
            "offset": offset,
            "limit": 30
        }

        try:
            response = requests.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()

            total = data.get('total', 0)
            items = data.get('items', [])

            log_message(f"Total videos: {total}, Items on this page: {len(items)}")

            # Process each item
            for item in items:
                video_id = item.get('id', '')
                status = item.get('status', '')
                duration = item.get('duration', 0)
                if status != 'past':
                    failed.append((video_id, f"Status is '{status}', not 'past'"))
                    continue
                if duration < min_time:
                    failed.append((video_id, f"Duration {duration}s is less than minimum {min_time}s"))
                    continue

                if duration > max_time:
                    failed.append((video_id, f"Duration {duration}s is greater than maximum {max_time}s"))
                    continue

                # Video passes all checks
                log_message(f"Video {video_id} is valid")
                succeeded.append(video_id)
            if page < end_page:
                time.sleep(2)

        except requests.exceptions.RequestException as e:
            log_message(f"Error fetching page {page}: {e}")
            continue
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

def enqueue_content_to_db(videoId: str, prepend_url="https://youtube.com/watch?v=") -> bool:
    server = SQLHandler()
    if server.check_row_exists("songs", "video_id", videoId):
        log_message(f"Video {videoId} already exists in the DB")
        return False
    log_message("Enqueuing content to the DB...")
    server.insert_row("archive_queue", "url, mode", (prepend_url+videoId, 0))
    return True


def main(args):
    """
    main function logic
    """

    if args.playlist:
        videos = youtube.get_videos_in_playlist(args.playlist)
        print(f"Scraping playlist complete. Total of {len(videos)} videos were found")
        for video_id, video_title in videos:
            print(f"Enqueueing {video_title} - {video_id}")
            enqueue_content_to_db(video_id)
        exit()

    if args.channel:
        succeeded, failed = youtube.get_content_youtube_channel(args.channel.strip(), args.min_time, args.max_time, args.wait_time)
        succeeded = list(set(succeeded))
        failed = list(set(failed))
        for vid_id, title in succeeded:
            print(f"Validated {vid_id} - {title} to API")
            if args.db:
                enqueue_content_to_db(vid_id)
            elif args.stub:
                with open("stub.txt", "a") as f:
                    f.write(f"{vid_id}\n")
            else:
                enqueue_content_to_api(vid_id)
        exit()

    if not args.youtube:
        # Default Holodex mode
        if args.direct_api:
            valid_video_ids, invalid_video_ids = get_content_headless_holodex(
                                                                    args.start_page,
                                                                    args.end_page,
                                                                    args.min_time,
                                                                    args.max_time
                                                                    )
        else:
            valid_video_ids, invalid_video_ids = get_content_holodex(os.getenv("HOLODEX_API_KEY"),
                                                                    args.start_page,
                                                                    args.end_page,
                                                                    args.min_time,
                                                                    args.max_time,
                                                                    args.wait_time
                                                                    )
        for vid_id in valid_video_ids:
            if args.db:
                enqueue_content_to_db(vid_id)
            elif args.stub:
                with open("stub.txt", "a") as f:
                    f.write(f"{vid_id}\n")
            else:
                enqueue_content_to_api(vid_id)
        generate_report(valid_video_ids, invalid_video_ids)
        return
    # YouTube mode
    if args.channel_id_source == "DB":
        pass # TODO: Read from DB in the future
    else:
        file = open(args.channel_id_source, "r")
        if not os.path.exists("logs"):
            os.makedirs("logs")
        for line in file:
            channel_id = line.strip()
            succeeded, failed = youtube.get_content_youtube_channel(channel_id, args.min_time, args.max_time, args.wait_time)
            succeeded = list(set(succeeded))
            failed = list(set(failed))
            for vid_id, title in succeeded:
                print(f"Validated {vid_id} - {title} to API")
                if args.db:
                    enqueue_content_to_db(vid_id)
                elif args.stub:
                    with open("stub.txt", "a") as f:
                        f.write(f"{vid_id}\n")
                else:
                    enqueue_content_to_api(vid_id)




if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="crawler.py", description="A script to crawl for content. Designed for Patchwork Archive")
    parser.add_argument("--start-page", type=int, default=1, help="The page to start scraping from")
    parser.add_argument("--end-page", type=int, default=1, help="The page to stop scraping at")
    parser.add_argument("--min-time", type=int, default=65, help="The minimum length of a video in seconds")
    parser.add_argument("--max-time", type=int, default=480, help="The maximum length of a video in seconds")
    parser.add_argument("--wait_time", type=int, default=5, help="The amount of time to wait for JS to load in sec (default=5)")
    parser.add_argument("--youtube", action="store_true", help="Scrape YouTube channels instead of Holodex")
    parser.add_argument("--playlist", type=str, help="Scrape a playlist instead of a channel by the YT playlist ID. Can only specify one playlist per run")
    parser.add_argument("--channel", type=str, help="Channel ID of YouTube Channel. Scrapes a singular channel for its contents")
    parser.add_argument("--db", action="store_true", help="Enqueue content to the DB instead of the API")
    parser.add_argument("--stub", action="store_true", help="Enqueue to a stub file instead of the API or DB")
    parser.add_argument("--channel_id_source", type=str, default="channels.txt", help="The file containing the channel IDs. Specify DB to use PostgreSQL DB via env variables")
    parser.add_argument("--detailed", action="store_true", help="Visits each video and checks for validity with more detail")
    parser.add_argument("--direct-api", action="store_true", help="Use direct API calls instead of browser scraping for Holodex")
    if parser.parse_args().stub:
        if not os.path.exists("stub.txt"):
            with open("stub.txt", "w") as f:
                f.write("Stub file for Patchwork Archive")
    if not load_dotenv():
        print("No .env file found. Please create one and try again. (Use the template)")
        quit()
    main(args=parser.parse_args())
