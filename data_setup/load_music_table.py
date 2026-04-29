# load_music_table.py
# This script loads songs from 2026a2_songs.json into the DynamoDB music table.

import json
import boto3
from botocore.exceptions import ClientError
from config import AWS_REGION, MUSIC_TABLE


# Create a DynamoDB resource
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
music_table = dynamodb.Table(MUSIC_TABLE)

# JSON file name
JSON_FILE_NAME = "2026a2_songs.json"


def load_json_file(file_name):
    """
    Load the songs JSON file and return the list of songs.
    """
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            data = json.load(file)

        songs = data.get("songs", [])
        print(f"Loaded {len(songs)} songs from {file_name}.")
        return songs

    except FileNotFoundError:
        print(f"File '{file_name}' not found.")
        return []
    except json.JSONDecodeError as error:
        print(f"Invalid JSON format in '{file_name}': {error}")
        return []
    except Exception as error:
        print(f"Unexpected error while reading '{file_name}': {error}")
        return []


def build_music_item(song):
    """
    Convert one song record from the JSON file into the format required
    for the DynamoDB music table.
    """
    title = song.get("title", "").strip()
    artist = song.get("artist", "").strip()
    year = str(song.get("year", "")).strip()
    album = song.get("album", "").strip()
    img_url = song.get("img_url", "").strip()

    title_year_album = f"{title}#{year}#{album}"
    year_album_title = f"{year}#{album}#{title}"
    artist_year_album = f"{artist}#{year}#{album}"

    item = {
        "artist": artist,
        "title_year_album": title_year_album,
        "title": title,
        "year": year,
        "album": album,
        "img_url": img_url,
        "image_s3_key": "",  # Will be updated later after S3 upload
        "year_album_title": year_album_title,
        "artist_year_album": artist_year_album
    }

    return item


def load_music_table():
    """
    Read the JSON file, transform each song into the required DynamoDB
    structure, and insert all songs into the music table.
    """
    songs = load_json_file(JSON_FILE_NAME)

    if not songs:
        print("No songs found to insert.")
        return

    inserted_count = 0

    try:
        with music_table.batch_writer() as batch:
            for song in songs:
                item = build_music_item(song)
                batch.put_item(Item=item)
                inserted_count += 1

        print(f"\nSuccessfully inserted {inserted_count} songs into the music table.")

    except ClientError as error:
        print(f"AWS ClientError while loading music table: {error}")
    except Exception as error:
        print(f"Unexpected error while loading music table: {error}")


if __name__ == "__main__":
    load_music_table()