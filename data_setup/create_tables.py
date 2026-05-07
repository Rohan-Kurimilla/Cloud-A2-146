
import boto3
from botocore.exceptions import ClientError

# ── AWS settings ───────────────────────────────────────────────────────────────
AWS_REGION = "us-east-1"

LOGIN_TBL = "login"
MUSIC_TBL = "music"
SUBS_TBL = "subscriptions"

# ── Index names ────────────────────────────────────────────────────────────────
GSI_BY_ARTIST = "artist-index"
LSI_BY_YEAR = "title-year-index"

# ── Boto3 setup ────────────────────────────────────────────────────────────────
db_resource = boto3.resource("dynamodb", region_name=AWS_REGION)


# ───────────────────────────────────────────────────────────────────────────────
# LOGIN TABLE
# ───────────────────────────────────────────────────────────────────────────────

def provision_login_table():

    try:
        tbl = db_resource.create_table(
            TableName=LOGIN_TBL,

            KeySchema=[
                {"AttributeName": "email", "KeyType": "HASH"},
            ],

            AttributeDefinitions=[
                {"AttributeName": "email", "AttributeType": "S"},
            ],

            BillingMode="PAY_PER_REQUEST",
        )

        print(f"[INFO] Waiting for '{LOGIN_TBL}' to become active...")
        tbl.wait_until_exists()

        print(f"[OK]   '{LOGIN_TBL}' is active and ready.")
        print(f"       Partition key → email")

        return tbl

    except ClientError as exc:
        err_code = exc.response["Error"]["Code"]

        if err_code == "ResourceInUseException":
            print(f"[SKIP] '{LOGIN_TBL}' already exists — skipping creation.")
            return db_resource.Table(LOGIN_TBL)

        raise


# ───────────────────────────────────────────────────────────────────────────────
# MUSIC TABLE
# ───────────────────────────────────────────────────────────────────────────────

def provision_music_table():

    key_definitions = [
        {"AttributeName": "title", "AttributeType": "S"},
        {"AttributeName": "artist#year", "AttributeType": "S"},
        {"AttributeName": "artist", "AttributeType": "S"},
        {"AttributeName": "year", "AttributeType": "S"},
    ]

    primary_key_schema = [
        {"AttributeName": "title", "KeyType": "HASH"},
        {"AttributeName": "artist#year", "KeyType": "RANGE"},
    ]

    gsi_definitions = [
        {
            "IndexName": GSI_BY_ARTIST,

            "KeySchema": [
                {"AttributeName": "artist", "KeyType": "HASH"},
                {"AttributeName": "year", "KeyType": "RANGE"},
            ],

            "Projection": {
                "ProjectionType": "ALL"
            },
        }
    ]

    lsi_definitions = [
        {
            "IndexName": LSI_BY_YEAR,

            "KeySchema": [
                {"AttributeName": "title", "KeyType": "HASH"},
                {"AttributeName": "year", "KeyType": "RANGE"},
            ],

            "Projection": {
                "ProjectionType": "ALL"
            },
        }
    ]

    try:
        tbl = db_resource.create_table(
            TableName=MUSIC_TBL,

            KeySchema=primary_key_schema,

            AttributeDefinitions=key_definitions,

            LocalSecondaryIndexes=lsi_definitions,

            GlobalSecondaryIndexes=gsi_definitions,

            BillingMode="PAY_PER_REQUEST",
        )

        print(f"[INFO] Waiting for '{MUSIC_TBL}' to become active...")
        tbl.wait_until_exists()

        print(f"[OK]   '{MUSIC_TBL}' is active and ready.")
        print(f"       Primary key  → title (PK) + artist#year (SK)")
        print(f"       GSI          → {GSI_BY_ARTIST}")
        print(f"       LSI          → {LSI_BY_YEAR}")

        return tbl

    except ClientError as exc:
        err_code = exc.response["Error"]["Code"]

        if err_code == "ResourceInUseException":
            print(f"[SKIP] '{MUSIC_TBL}' already exists — skipping creation.")
            return db_resource.Table(MUSIC_TBL)

        raise


# ───────────────────────────────────────────────────────────────────────────────
# SUBSCRIPTIONS TABLE
# ───────────────────────────────────────────────────────────────────────────────

def provision_subscriptions_table():

    pk_schema = [
        {"AttributeName": "email", "KeyType": "HASH"},
        {"AttributeName": "song_id", "KeyType": "RANGE"},
    ]

    attr_defs = [
        {"AttributeName": "email", "AttributeType": "S"},
        {"AttributeName": "song_id", "AttributeType": "S"},
    ]

    try:
        tbl = db_resource.create_table(
            TableName=SUBS_TBL,

            KeySchema=pk_schema,

            AttributeDefinitions=attr_defs,

            BillingMode="PAY_PER_REQUEST",
        )

        print(f"[INFO] Waiting for '{SUBS_TBL}' to become active...")
        tbl.wait_until_exists()

        print(f"[OK]   '{SUBS_TBL}' is active and ready.")
        print(f"       Partition key → email")
        print(f"       Sort key      → song_id")

        return tbl

    except ClientError as exc:
        err_code = exc.response["Error"]["Code"]

        if err_code == "ResourceInUseException":
            print(f"[SKIP] '{SUBS_TBL}' already exists — skipping creation.")
            return db_resource.Table(SUBS_TBL)

        raise


# ───────────────────────────────────────────────────────────────────────────────
# MAIN
# ───────────────────────────────────────────────────────────────────────────────

def run():

    provision_login_table()
    provision_music_table()
    provision_subscriptions_table()

    print("\n[DONE] All DynamoDB tables are ready.")


if __name__ == "__main__":
    run()