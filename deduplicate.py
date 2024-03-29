# A simple script to deduplicate a list of Channel IDs

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
shuffle_file("channels.txt")