# seed_login_table.py
# This script inserts the 10 required login records into the login table.

import boto3
from botocore.exceptions import ClientError
from config import AWS_REGION, LOGIN_TABLE, GROUP_BASE_STUDENT_ID, GROUP_BASE_NAME, SEED_PASSWORDS


# Create a DynamoDB resource
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
login_table = dynamodb.Table(LOGIN_TABLE)


def build_login_records():
    """
    Build the 10 login records required by the assignment.
    Example email format:
    s1234567+0@student.rmit.edu.au
    """
    records = []

    for i in range(10):
        email = f"{GROUP_BASE_STUDENT_ID}+{i}@student.rmit.edu.au"
        user_name = f"{GROUP_BASE_NAME}{i}"
        password = SEED_PASSWORDS[i]

        records.append({
            "email": email,
            "user_name": user_name,
            "password": password
        })

    return records


def seed_login_table():
    """
    Insert the generated login records into the DynamoDB login table.
    """
    records = build_login_records()

    try:
        with login_table.batch_writer() as batch:
            for record in records:
                batch.put_item(Item=record)

        print("Successfully inserted 10 login records into the login table.\n")

        print("Inserted records:")
        for record in records:
            print(record)

    except ClientError as error:
        print(f"AWS ClientError while seeding login table: {error}")
    except Exception as error:
        print(f"Unexpected error while seeding login table: {error}")


if __name__ == "__main__":
    seed_login_table()