# update_music_s3_keys.py
# This script updates each music record with its corresponding S3 image key.

import boto3
from botocore.exceptions import ClientError
from config import AWS_REGION, MUSIC_TABLE


# Create DynamoDB resource
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
music_table = dynamodb.Table(MUSIC_TABLE)


def clean_artist_name(name):
    """
    Convert artist name into the same safe filename format
    used during image upload.
    """
    return name.replace(" ", "").replace("&", "").replace(".", "").replace("/", "")


def get_all_music_items():
    """
    Scan the music table and return all items.
    """
    items = []
    response = music_table.scan()
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = music_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    return items


def update_image_s3_key(item):
    """
    Update one music item with its corresponding S3 image key.
    """
    artist = item["artist"]
    title_year_album = item["title_year_album"]

    filename = clean_artist_name(artist) + ".jpg"
    image_s3_key = f"artists/{filename}"

    try:
        music_table.update_item(
            Key={
                "artist": artist,
                "title_year_album": title_year_album
            },
            UpdateExpression="SET image_s3_key = :s3key",
            ExpressionAttributeValues={
                ":s3key": image_s3_key
            }
        )
        print(f"Updated: {artist} | {title_year_album} -> {image_s3_key}")

    except ClientError as error:
        print(f"AWS ClientError updating {artist} | {title_year_album}: {error}")
    except Exception as error:
        print(f"Unexpected error updating {artist} | {title_year_album}: {error}")


def main():
    print("Fetching all music items from DynamoDB...")
    items = get_all_music_items()
    print(f"Found {len(items)} music items.\n")

    for item in items:
        update_image_s3_key(item)

    print("\nFinished updating image_s3_key for all music items.")


if __name__ == "__main__":
    main()