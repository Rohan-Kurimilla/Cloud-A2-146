# config.py
# Shared configuration for Member 1 scripts

AWS_REGION = "us-east-1"   # Change if your AWS lab uses a different region

LOGIN_TABLE = "login"
MUSIC_TABLE = "music"
SUBSCRIPTIONS_TABLE = "subscriptions"

# Use your actual S3 bucket name later
S3_BUCKET_NAME = "myassignment2bucket-ashup"

# These are placeholders for now.
# Replace them later when your group leader/base identity is decided.
GROUP_BASE_STUDENT_ID = "s4109620"
GROUP_BASE_NAME = "Ashutosh Panda"

# Seed passwords based on the assignment pattern
SEED_PASSWORDS = [
    "012345",
    "123456",
    "234567",
    "345678",
    "456789",
    "567890",
    "678901",
    "789012",
    "890123",
    "901234"
]