import re
from bs4 import BeautifulSoup
from site_scraper import SiteScraper

music_keywords = [
    "cover", "original", "mv", "歌ってみた", "covered by", "official", "オリジナル曲"
]

def find_all_yt_video_ids_hldex(source: str) -> list[str]:
    """
    Find all YouTube video IDs in the given source
    :param source: The page source to search for video IDs
    :return: A list of video IDs
    """
    return list(set(re.findall(r'href="/watch/(\w+)"', source)))


def find_all_yt_videos_yt(source: str) -> list[str, str]:
    """
    Find all YouTube video IDs in the given source and their titles
    :param source: The page source to search for video IDs
    :return: A list of video IDs
    """
    soup = BeautifulSoup(source, "html.parser")
    videos = []
    video_ids = set()  # to store unique video IDs
    for h3_tag in soup.find_all('h3', class_='style-scope ytd-rich-grid-media'):
        a_tag = h3_tag.find('a', id='video-title-link')
        if a_tag:
            href = a_tag.get('href')
            title = a_tag.get('title')
            if href and title:
                video_id = re.search(r'/watch\?v=(\w+)', href)
                # check if video_id is valid youtube video id and not already in video_ids set
                if video_id and len(video_id.group(1)) >= 11 and video_id.group(1) not in video_ids:
                    video_ids.add(video_id.group(1))  # add video_id to set
                    videos.append((video_id.group(1), title))
    return videos


def parse_title_yt_video(source: str) -> str:
    """
    Parse the title of a YouTube video
    :param source: The page source to search for the title
    :return: The title of the video
    """
    title = re.search(r'<title>(.*?)</title>', source).group(1)
    title = title.replace(" - YouTube", "")
    return title

def is_potentially_music_content(title: str)-> tuple[bool, str]:
    """
    Given a title, determine if the content is music or not
    """
    # Stage 1: Preliminary Keyword Checks
    title = title.lower()
    if not any(keyword in title for keyword in music_keywords):
        return False, "No music keywords found"
    return True, "Valid music content"

