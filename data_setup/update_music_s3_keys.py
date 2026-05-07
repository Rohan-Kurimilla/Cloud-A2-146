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
    Convert artist name into a safe filename format.
    """
    return (
        name.replace(" ", "")
            .replace("&", "")
            .replace(".", "")
            .replace("/", "")
    )


def get_all_music_items():
    """
    Scan the music table and return all items.
    """
    items = []

    response = music_table.scan()

    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:

        response = music_table.scan(
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )

        items.extend(response.get("Items", []))

    return items


def update_image_s3_key(item):
    """
    Update one music item with its corresponding S3 image key.
    """

    title = item["title"]

    # Primary sort key in your schema
    artist_year = item["artist#year"]

    artist = item["artist"]

    # Build filename
    filename = clean_artist_name(artist) + ".jpg"

    image_s3_key = f"artists/{filename}"

    try:
        music_table.update_item(

            Key={
                "title": title,
                "artist#year": artist_year
            },

            UpdateExpression="SET image_s3_key = :s3key",

            ExpressionAttributeValues={
                ":s3key": image_s3_key
            }
        )

        print(f"Updated: {title} | {artist_year} -> {image_s3_key}")

    except ClientError as error:

        print(
            f"AWS ClientError updating {title} | {artist_year}: {error}"
        )

    except Exception as error:

        print(
            f"Unexpected error updating {title} | {artist_year}: {error}"
        )


def main():

    print("Fetching all music items from DynamoDB...")

    items = get_all_music_items()

    print(f"Found {len(items)} music items.\n")

    for item in items:
        update_image_s3_key(item)

    print("\nFinished updating image_s3_key for all music items.")


if __name__ == "__main__":
    main()