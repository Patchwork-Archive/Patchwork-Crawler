from site_scraper  import SiteScraper
from source_parse import find_all_yt_videos_yt, parse_title_yt_video, is_potentially_music_content
import yt_dlp
import os

def scrape_yt_channel_videos(channel_url: str, scraper: SiteScraper) -> tuple[str, str]:
    """
    Scrapes a YouTube channel for all videos and their titles
    """
    channel_video_raw_data = scraper.get_page_source(channel_url)
    video_tuples = find_all_yt_videos_yt(channel_video_raw_data)
    return video_tuples

def get_content_youtube(channel_id: str, min_time: int = 65, max_time: int = 480, wait_time: int = 5) -> tuple[list[str], list[tuple[str, str]]]:
    if not channel_id.startswith("UC") or not len(channel_id) == 24:
        print("[Error] Invalid Channel ID provided " + channel_id)
        return
    chrome_driver_path = os.getenv("CHROME_DRIVER_PATH")
    if chrome_driver_path is None:
        chrome_driver_path = "/usr/bin/chromedriver"
    scraper = SiteScraper(chrome_driver_path=chrome_driver_path)
    succeeded = []
    failed = []
    ytdl = yt_dlp.YoutubeDL()
    video_data = scrape_yt_channel_videos("https://www.youtube.com/channel/"+channel_id+"/videos", scraper)
    for video_id, title in video_data:
        music_flag = is_potentially_music_content(title)
        if music_flag[0]: # Check if the video is music content
            # Stage 2. Check length of video
            ytdl.extract_info(video_id, download=False)
            video_info = ytdl.extract_info(video_id, download=False)
            if video_info.get('duration') is not None:
                duration = video_info.get('duration')
                if duration > min_time and duration < max_time:
                    print(f"[YouTube Parse] Video {video_id} is valid")
                    succeeded.append((video_id, title))
                else:
                    print(f"[YouTube Parse] Video {video_id} is not valid: Duration not within specified range")
                    failed.append((video_id, "Duration not within specified range"))
            else:
                print(f"[YouTube Parse] Video {video_id} is not valid: No duration found")
                failed.append((video_id, "No duration found"))
            succeeded.append((video_id, title))
        else:
            print(f"[YouTube Parse] Video {video_id} is not valid: Not music content")
            failed.append((video_id, "Not music content"))
    scraper.close()
    return succeeded, failed
