# create_tables.py
# This script creates the DynamoDB tables required for the assignment:
# 1. login
# 2. music
# 3. subscriptions

import boto3
from botocore.exceptions import ClientError
from config import AWS_REGION, LOGIN_TABLE, MUSIC_TABLE, SUBSCRIPTIONS_TABLE


# Create a DynamoDB client
dynamodb = boto3.client("dynamodb", region_name=AWS_REGION)


def table_exists(table_name):
    """
    Check whether a DynamoDB table already exists.
    Returns True if it exists, otherwise False.
    """
    try:
        dynamodb.describe_table(TableName=table_name)
        return True
    except dynamodb.exceptions.ResourceNotFoundException:
        return False
    except ClientError as error:
        print(f"Error checking table '{table_name}': {error}")
        raise


def wait_for_table(table_name):
    """
    Wait until the table becomes active.
    """
    print(f"Waiting for table '{table_name}' to become active...")
    waiter = dynamodb.get_waiter("table_exists")
    waiter.wait(TableName=table_name)
    print(f"Table '{table_name}' is now active.\n")


def create_login_table():
    """
    Create the login table with:
    - Partition Key: email
    """
    if table_exists(LOGIN_TABLE):
        print(f"Table '{LOGIN_TABLE}' already exists. Skipping creation.\n")
        return

    print(f"Creating table '{LOGIN_TABLE}'...")

    dynamodb.create_table(
        TableName=LOGIN_TABLE,
        AttributeDefinitions=[
            {"AttributeName": "email", "AttributeType": "S"}
        ],
        KeySchema=[
            {"AttributeName": "email", "KeyType": "HASH"}
        ],
        BillingMode="PAY_PER_REQUEST"
    )

    wait_for_table(LOGIN_TABLE)


def create_music_table():
    """
    Create the music table with:
    - Partition Key: artist
    - Sort Key: title_year_album

    Local Secondary Index (LSI):
    - artist + year_album_title

    Global Secondary Index (GSI):
    - title + artist_year_album
    """
    if table_exists(MUSIC_TABLE):
        print(f"Table '{MUSIC_TABLE}' already exists. Skipping creation.\n")
        return

    print(f"Creating table '{MUSIC_TABLE}'...")

    dynamodb.create_table(
        TableName=MUSIC_TABLE,
        AttributeDefinitions=[
            {"AttributeName": "artist", "AttributeType": "S"},
            {"AttributeName": "title_year_album", "AttributeType": "S"},
            {"AttributeName": "year_album_title", "AttributeType": "S"},
            {"AttributeName": "title", "AttributeType": "S"},
            {"AttributeName": "artist_year_album", "AttributeType": "S"}
        ],
        KeySchema=[
            {"AttributeName": "artist", "KeyType": "HASH"},
            {"AttributeName": "title_year_album", "KeyType": "RANGE"}
        ],
        LocalSecondaryIndexes=[
            {
                "IndexName": "artist-year-album-title-lsi",
                "KeySchema": [
                    {"AttributeName": "artist", "KeyType": "HASH"},
                    {"AttributeName": "year_album_title", "KeyType": "RANGE"}
                ],
                "Projection": {
                    "ProjectionType": "ALL"
                }
            }
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "title-artist-year-album-gsi",
                "KeySchema": [
                    {"AttributeName": "title", "KeyType": "HASH"},
                    {"AttributeName": "artist_year_album", "KeyType": "RANGE"}
                ],
                "Projection": {
                    "ProjectionType": "ALL"
                }
            }
        ],
        BillingMode="PAY_PER_REQUEST"
    )

    wait_for_table(MUSIC_TABLE)


def create_subscriptions_table():
    """
    Create the subscriptions table with:
    - Partition Key: email
    - Sort Key: music_id
    """
    if table_exists(SUBSCRIPTIONS_TABLE):
        print(f"Table '{SUBSCRIPTIONS_TABLE}' already exists. Skipping creation.\n")
        return

    print(f"Creating table '{SUBSCRIPTIONS_TABLE}'...")

    dynamodb.create_table(
        TableName=SUBSCRIPTIONS_TABLE,
        AttributeDefinitions=[
            {"AttributeName": "email", "AttributeType": "S"},
            {"AttributeName": "music_id", "AttributeType": "S"}
        ],
        KeySchema=[
            {"AttributeName": "email", "KeyType": "HASH"},
            {"AttributeName": "music_id", "KeyType": "RANGE"}
        ],
        BillingMode="PAY_PER_REQUEST"
    )

    wait_for_table(SUBSCRIPTIONS_TABLE)


def main():
    """
    Main function to create all required tables.
    """
    try:
        create_login_table()
        create_music_table()
        create_subscriptions_table()
        print("All required tables are ready.")
    except ClientError as error:
        print(f"AWS ClientError: {error}")
    except Exception as error:
        print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()