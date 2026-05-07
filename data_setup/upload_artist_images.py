# upload_artist_images.py
# This script downloads artist images from URLs and uploads them to S3.

import os
import requests
import boto3
from urllib.parse import urlparse
from config import AWS_REGION, MUSIC_TABLE, S3_BUCKET_NAME

# DynamoDB
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
music_table = dynamodb.Table(MUSIC_TABLE)

# S3 client
s3 = boto3.client("s3", region_name=AWS_REGION)

# Temp folder
TEMP_FOLDER = "temp_images"


def create_temp_folder():
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)


def get_unique_images():
    """
    Get unique image URLs from music table
    """
    response = music_table.scan()
    items = response.get("Items", [])

    image_map = {}

    for item in items:
        url = item.get("image_url")
        artist = item.get("artist")

        if url and artist:
            image_map[url] = artist

    return image_map


def clean_artist_name(name):
    return name.replace(" ", "").replace("&", "").replace(".", "")


def download_image(url, artist):
    """
    Download image from URL
    """
    try:
        response = requests.get(url)
        if response.status_code == 200:
            filename = clean_artist_name(artist) + ".jpg"
            filepath = os.path.join(TEMP_FOLDER, filename)

            with open(filepath, "wb") as file:
                file.write(response.content)

            return filepath, f"artists/{filename}"

    except Exception as e:
        print(f"Download failed: {url} → {e}")

    return None, None


def upload_to_s3(filepath, s3_key):
    """
    Upload image to S3
    """
    try:
        s3.upload_file(filepath, S3_BUCKET_NAME, s3_key)
        print(f"Uploaded: {s3_key}")
    except Exception as e:
        print(f"S3 upload failed: {e}")


def main():
    print("Fetching unique images...")
    image_map = get_unique_images()

    print(f"Found {len(image_map)} unique images.\n")

    create_temp_folder()

    for url, artist in image_map.items():
        filepath, s3_key = download_image(url, artist)

        if filepath:
            upload_to_s3(filepath, s3_key)

    print("\nAll images processed.")


if __name__ == "__main__":
    main()