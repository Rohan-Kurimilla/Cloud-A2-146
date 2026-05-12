# config.py
# Configuration for Member 3 Backend (Flask API)

AWS_REGION = "us-east-1"

# DynamoDB table names (must match Member 1)
LOGIN_TABLE = "login"
MUSIC_TABLE = "music"
SUBSCRIPTIONS_TABLE = "subscriptions"

# S3 bucket (same as Member 1)
S3_BUCKET_NAME = "myassignment2bucket-ashup"

# Base URL for accessing S3 images
S3_BASE_URL = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/"