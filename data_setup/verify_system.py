# verify_system.py
# This script verifies login, music query, and subscription functionality.

import boto3
from config import AWS_REGION, LOGIN_TABLE, MUSIC_TABLE, SUBSCRIPTIONS_TABLE

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

login_table = dynamodb.Table(LOGIN_TABLE)
music_table = dynamodb.Table(MUSIC_TABLE)
subscriptions_table = dynamodb.Table(SUBSCRIPTIONS_TABLE)


# -----------------------------
# TEST 1: LOGIN CHECK
# -----------------------------
def test_login():
    print("\n--- TEST 1: LOGIN ---")

    email = "s1234567+0@student.rmit.edu.au"

    response = login_table.get_item(Key={"email": email})
    item = response.get("Item")

    if item:
        print(f"Login user found: {item['user_name']}")
    else:
        print("Login failed")


# -----------------------------
# TEST 2: QUERY MUSIC BY ARTIST
# -----------------------------
def test_music_query():
    print("\n--- TEST 2: MUSIC QUERY (Artist) ---")

    artist = "Taylor Swift"

    response = music_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("artist").eq(artist)
    )

    items = response.get("Items", [])

    print(f"Found {len(items)} songs for {artist}")

    for item in items[:3]:  # show first 3 only
        print(f"- {item['title']} ({item['year']})")


# -----------------------------
# TEST 3: ADD SUBSCRIPTION
# -----------------------------
def test_add_subscription():
    print("\n--- TEST 3: ADD SUBSCRIPTION ---")

    email = "s1234567+0@student.rmit.edu.au"

    # get one song
    response = music_table.scan(Limit=1)
    song = response["Items"][0]

    music_id = f"{song['artist']}#{song['title']}#{song['year']}#{song['album']}"

    subscriptions_table.put_item(
        Item={
            "email": email,
            "music_id": music_id,
            "title": song["title"],
            "artist": song["artist"],
            "year": song["year"],
            "album": song["album"],
            "image_s3_key": song["image_s3_key"]
        }
    )

    print(f"Subscribed to: {song['title']}")


# -----------------------------
# TEST 4: VIEW SUBSCRIPTIONS
# -----------------------------
def test_view_subscriptions():
    print("\n--- TEST 4: VIEW SUBSCRIPTIONS ---")

    email = "s1234567+0@student.rmit.edu.au"

    response = subscriptions_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(email)
    )

    items = response.get("Items", [])

    print(f"Total subscriptions: {len(items)}")

    for item in items:
        print(f"- {item['title']} ({item['artist']})")


# -----------------------------
# TEST 5: REMOVE SUBSCRIPTION
# -----------------------------
def test_remove_subscription():
    print("\n--- TEST 5: REMOVE SUBSCRIPTION ---")

    email = "s1234567+0@student.rmit.edu.au"

    response = subscriptions_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(email)
    )

    items = response.get("Items", [])

    if items:
        item = items[0]

        subscriptions_table.delete_item(
            Key={
                "email": email,
                "music_id": item["music_id"]
            }
        )

        print(f"Removed: {item['title']}")
    else:
        print("No subscriptions to remove")


# -----------------------------
# MAIN
# -----------------------------
def main():
    test_login()
    test_music_query()
    test_add_subscription()
    test_view_subscriptions()
    test_remove_subscription()
    test_view_subscriptions()


if __name__ == "__main__":
    main()