# app.py
# Flask backend API for AWS Music Subscription App

from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from config import (
    AWS_REGION,
    LOGIN_TABLE,
    MUSIC_TABLE,
    SUBSCRIPTIONS_TABLE,
    S3_BASE_URL
)

app = Flask(__name__)
CORS(app)

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

login_table = dynamodb.Table(LOGIN_TABLE)
music_table = dynamodb.Table(MUSIC_TABLE)
subscriptions_table = dynamodb.Table(SUBSCRIPTIONS_TABLE)


def add_full_image_url(item):
    """Attach full S3 image URL to a music/subscription item."""
    image_key = item.get("image_s3_key", "")
    item["image_url"] = S3_BASE_URL + image_key if image_key else ""
    return item


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "AWS Music Subscription Backend is running"
    })


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"success": False, "message": "email or password is invalid"}), 400

    response = login_table.get_item(Key={"email": email})
    user = response.get("Item")

    if not user or user.get("password") != password:
        return jsonify({"success": False, "message": "email or password is invalid"}), 401

    return jsonify({
        "success": True,
        "message": "login successful",
        "user_name": user.get("user_name"),
        "email": user.get("email")
    })


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    email = data.get("email")
    user_name = data.get("user_name")
    password = data.get("password")

    if not email or not user_name or not password:
        return jsonify({"success": False, "message": "missing required fields"}), 400

    response = login_table.get_item(Key={"email": email})

    if "Item" in response:
        return jsonify({"success": False, "message": "The email already exists"}), 409

    login_table.put_item(
        Item={
            "email": email,
            "user_name": user_name,
            "password": password
        }
    )

    return jsonify({
        "success": True,
        "message": "registration successful"
    })


@app.route("/songs", methods=["GET"])
def query_songs():
    title = request.args.get("title", "").strip()
    artist = request.args.get("artist", "").strip()
    year = request.args.get("year", "").strip()
    album = request.args.get("album", "").strip()

    if not any([title, artist, year, album]):
        return jsonify({
            "success": False,
            "message": "At least one query field is required",
            "songs": []
        }), 400

    try:
        # Best case: artist query using partition key
        if artist:
            response = music_table.query(
                KeyConditionExpression=Key("artist").eq(artist)
            )
            songs = response.get("Items", [])

        # Title-only or title-first search using GSI
        elif title:
            response = music_table.query(
                IndexName="title-artist-year-album-gsi",
                KeyConditionExpression=Key("title").eq(title)
            )
            songs = response.get("Items", [])

        # Other cases need Scan
        else:
            filter_expression = None

            if year:
                filter_expression = Attr("year").eq(year)

            if album:
                album_filter = Attr("album").eq(album)
                filter_expression = album_filter if filter_expression is None else filter_expression & album_filter

            response = music_table.scan(FilterExpression=filter_expression)
            songs = response.get("Items", [])

        # Apply AND filters after initial efficient query
        filtered_songs = []

        for song in songs:
            if title and song.get("title") != title:
                continue
            if artist and song.get("artist") != artist:
                continue
            if year and song.get("year") != year:
                continue
            if album and song.get("album") != album:
                continue

            filtered_songs.append(add_full_image_url(song))

        if not filtered_songs:
            return jsonify({
                "success": True,
                "message": "No result is retrieved. Please query again",
                "songs": []
            })

        return jsonify({
            "success": True,
            "message": "songs retrieved successfully",
            "songs": filtered_songs
        })

    except ClientError as error:
        return jsonify({"success": False, "error": str(error)}), 500


@app.route("/subscriptions", methods=["GET"])
def get_subscriptions():
    email = request.args.get("email", "").strip()

    if not email:
        return jsonify({"success": False, "message": "email is required"}), 400

    response = subscriptions_table.query(
        KeyConditionExpression=Key("email").eq(email)
    )

    subscriptions = response.get("Items", [])
    subscriptions = [add_full_image_url(item) for item in subscriptions]

    return jsonify({
        "success": True,
        "subscriptions": subscriptions
    })


@app.route("/subscriptions", methods=["POST"])
def add_subscription():
    data = request.get_json()

    email = data.get("email")
    title = data.get("title")
    artist = data.get("artist")
    year = data.get("year")
    album = data.get("album")
    image_s3_key = data.get("image_s3_key", "")

    if not all([email, title, artist, year, album]):
        return jsonify({"success": False, "message": "missing required fields"}), 400

    music_id = f"{artist}#{title}#{year}#{album}"

    subscriptions_table.put_item(
        Item={
            "email": email,
            "music_id": music_id,
            "title": title,
            "artist": artist,
            "year": year,
            "album": album,
            "image_s3_key": image_s3_key
        }
    )

    return jsonify({
        "success": True,
        "message": "subscription added successfully"
    })


@app.route("/subscriptions", methods=["DELETE"])
def remove_subscription():
    data = request.get_json()

    email = data.get("email")
    music_id = data.get("music_id")

    if not email or not music_id:
        return jsonify({"success": False, "message": "email and music_id are required"}), 400

    subscriptions_table.delete_item(
        Key={
            "email": email,
            "music_id": music_id
        }
    )

    return jsonify({
        "success": True,
        "message": "subscription removed successfully"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)