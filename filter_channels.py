import requests
from tqdm import tqdm
import concurrent.futures

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
