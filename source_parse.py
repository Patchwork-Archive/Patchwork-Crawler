import re

def find_all_yt_video_ids(source: str) -> list[str]:
    """
    Find all YouTube video IDs in the given source
    :param source: The page source to search for video IDs
    :return: A list of video IDs
    """
    return list(set(re.findall(r'href="/watch/(\w+)"', source)))
