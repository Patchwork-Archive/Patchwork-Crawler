# A simple script to deduplicate a list of Channel IDs
# and also other various tools for managing the channel list
import requests
from tqdm import tqdm
import concurrent.futures


def deduplicate_channel_ids(file_path: str = ""):
    """
    Deduplicate a list of channel IDs
    :param file_path: The path to the file containing the channel IDs
    """
    with open(file_path, "r") as f:
        channel_ids = f.readlines()
    channel_ids = [channel_id.strip() for channel_id in channel_ids]
    channel_ids = list(set(channel_ids))
    with open(file_path, "w") as f:
        for channel_id in channel_ids:
            f.write(f"{channel_id}\n")
    print("Deduplication complete")

def shuffle_file(file_path: str = ""):
    import random
    """
    Shuffle the lines in a file
    :param file_path: The path to the file to shuffle
    """
    with open(file_path, "r") as f:
        lines = f.readlines()
    random.shuffle(lines)
    with open(file_path, "w") as f:
        for line in lines:
            f.write(line)

def pull_channel_file():
    remote_url = "https://raw.githubusercontent.com/Patchwork-Archive/Patchwork-Data/main/channels.txt"
    local_path = "appended_channels.txt"
    response = requests.get(remote_url)
    if response.status_code == 200:
        with open(local_path, "w") as f:
            f.write(response.text)
        print("File downloaded successfully")
    else:
        print("Failed to download file")

def remove_topic_channels():
    with open("appended_channels.txt", "r") as f:
        lines = f.readlines()
    with open("appended_channels.txt", "w") as f:
        for line in lines:
            if "Topic" not in line and "[Error]" not in line:
                f.write(line)

def deappend_channels():
    with open("appended_channels.txt", "r") as f:
        lines = f.readlines()
    with open("channels.txt", "w") as f:
        for line in lines:
            f.write(line.split(" - ")[0].strip() + "\n")

def process_channel(channel_id):
    response = requests.get(f"https://www.youtube.com/channel/{channel_id}")
    if response.status_code == 200:
        try:
            channel_name = response.text.split('<meta property="og:title" content="')[1].split('">')[0]
        except:
            channel_name = "[Error] Channel name not found"
        return f"{channel_id} - {channel_name}\n"
    else:
        return f"{channel_id} - [Error] Channel not found\n"

def process_helper():
    with open("appended_channels.txt", "w") as f:
        with open("channels.txt", "r") as c:
            total_lines = sum(1 for _ in c)  # Count the total number of lines in the file
            c.seek(0)  # Reset the file pointer to the beginning

            with concurrent.futures.ThreadPoolExecutor() as executor:
                channel_ids = [line.strip() for line in c]
                results = list(tqdm(executor.map(process_channel, channel_ids), total=total_lines, desc="Processing channels"))
                f.writelines(results)

pull_channel_file()
remove_topic_channels()
deduplicate_channel_ids("appended_channels.txt")
deappend_channels()
shuffle_file("channels.txt")