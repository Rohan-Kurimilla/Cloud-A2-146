import json
import boto3
from boto3.dynamodb.conditions import Key, Attr

AWS_REGION = "us-east-1"

LOGIN_TABLE         = "login"
MUSIC_TABLE         = "music"
SUBSCRIPTIONS_TABLE = "subscriptions"

S3_BUCKET_NAME = "music-app-images-kingston-4156256-2026"
S3_BASE_URL    = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/"

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

login_table         = dynamodb.Table(LOGIN_TABLE)
music_table         = dynamodb.Table(MUSIC_TABLE)
subscriptions_table = dynamodb.Table(SUBSCRIPTIONS_TABLE)


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS"
        },
        "body": json.dumps(body)
    }


def get_body(event):
    if not event.get("body"):
        return {}
    try:
        return json.loads(event["body"])
    except Exception:
        return {}


def add_image_url(item):
    image_key = item.get("image_s3_key", "")
    item["image_url"] = S3_BASE_URL + image_key if image_key else ""
    return item


def handle_home():
    return response(200, {"message": "AWS Music Subscription Lambda Backend is running"})


def handle_login(event):
    data = get_body(event)

    email    = data.get("email")
    password = data.get("password")

    if not email or not password:
        return response(400, {"success": False, "message": "email or password is invalid"})

    result = login_table.get_item(Key={"email": email})
    user   = result.get("Item")

    if not user or user.get("password") != password:
        return response(401, {"success": False, "message": "email or password is invalid"})

    return response(200, {
        "success":   True,
        "message":   "login successful",
        "email":     user.get("email"),
        "user_name": user.get("user_name")
    })


def handle_register(event):
    data = get_body(event)

    email     = data.get("email")
    user_name = data.get("user_name")
    password  = data.get("password")

    if not email or not user_name or not password:
        return response(400, {"success": False, "message": "missing required fields"})

    existing = login_table.get_item(Key={"email": email})
    if "Item" in existing:
        return response(409, {"success": False, "message": "The email already exists"})

    login_table.put_item(Item={"email": email, "user_name": user_name, "password": password})

    return response(201, {"success": True, "message": "registration successful"})


def handle_get_songs(event):
    params = event.get("queryStringParameters") or {}

    title  = (params.get("title")  or "").strip()
    artist = (params.get("artist") or "").strip()
    year   = (params.get("year")   or "").strip()
    album  = (params.get("album")  or "").strip()

    if not any([title, artist, year, album]):
        return response(400, {
            "success": False,
            "message": "At least one query field is required",
            "songs": []
        })

    # Artist search — uses the artist-index GSI (artist is NOT the base table PK)
    # FIXED: added IndexName="artist-index"; without it DynamoDB raises ValidationException
    if artist:
        result = music_table.query(
            IndexName="artist-index",
            KeyConditionExpression=Key("artist").eq(artist)
        )
        songs = result.get("Items", [])

    # Title-only search — title IS the base table partition key; no index needed
    # FIXED: removed the wrong IndexName="title-artist-year-album-gsi" (never existed)
    elif title:
        result = music_table.query(
            KeyConditionExpression=Key("title").eq(title)
        )
        songs = result.get("Items", [])

    # Year / album only — need a full scan with filter
    else:
        filter_expression = None

        if year:
            filter_expression = Attr("year").eq(year)

        if album:
            album_filter = Attr("album").eq(album)
            filter_expression = album_filter if filter_expression is None else filter_expression & album_filter

        result = music_table.scan(FilterExpression=filter_expression)
        songs  = result.get("Items", [])

    # Apply remaining AND filters in Python after the DynamoDB call
    filtered_songs = []
    for song in songs:
        if title  and song.get("title")  != title:  continue
        if artist and song.get("artist") != artist: continue
        if year   and song.get("year")   != year:   continue
        if album  and song.get("album")  != album:  continue
        filtered_songs.append(add_image_url(song))

    if not filtered_songs:
        return response(200, {
            "success": True,
            "message": "No result is retrieved. Please query again",
            "songs": []
        })

    return response(200, {
        "success": True,
        "message": "songs retrieved successfully",
        "songs":   filtered_songs
    })


def handle_get_subscriptions(event):
    params = event.get("queryStringParameters") or {}
    email  = (params.get("email") or "").strip()

    if not email:
        return response(400, {"success": False, "message": "email is required"})

    result        = subscriptions_table.query(KeyConditionExpression=Key("email").eq(email))
    subscriptions = [add_image_url(item) for item in result.get("Items", [])]

    return response(200, {"success": True, "subscriptions": subscriptions})


def handle_add_subscription(event):
    data = get_body(event)

    email        = data.get("email")
    title        = data.get("title")
    artist       = data.get("artist")
    year         = data.get("year")
    album        = data.get("album")
    image_s3_key = data.get("image_s3_key", "")

    if not all([email, title, artist, year, album]):
        return response(400, {"success": False, "message": "missing required fields"})

    music_id = f"{artist}#{title}#{year}#{album}"

    subscriptions_table.put_item(
        Item={
            "email":        email,
            "music_id":     music_id,
            "title":        title,
            "artist":       artist,
            "year":         year,
            "album":        album,
            "image_s3_key": image_s3_key
        }
    )

    return response(201, {"success": True, "message": "subscription added successfully"})


def handle_delete_subscription(event):
    data = get_body(event)

    email    = data.get("email")
    music_id = data.get("music_id")

    if not email or not music_id:
        return response(400, {"success": False, "message": "email and music_id are required"})

    subscriptions_table.delete_item(Key={"email": email, "music_id": music_id})

    return response(200, {"success": True, "message": "subscription removed successfully"})


def lambda_handler(event, context):
    method = event.get("httpMethod", "")
    path   = event.get("path", "")

    if method == "OPTIONS":
        return response(200, {"message": "CORS preflight successful"})

    if path in ["/", "/music"] and method == "GET":
        return handle_home()

    if path == "/login"        and method == "POST":   return handle_login(event)
    if path == "/register"     and method == "POST":   return handle_register(event)
    if path == "/songs"        and method == "GET":    return handle_get_songs(event)
    if path == "/subscriptions" and method == "GET":   return handle_get_subscriptions(event)
    if path == "/subscriptions" and method == "POST":  return handle_add_subscription(event)
    if path == "/subscriptions" and method == "DELETE": return handle_delete_subscription(event)

    return response(404, {"success": False, "message": f"No route found for {method} {path}"})
