# Cloud-A2-146 — Sonata Music Subscription App

A cloud-native music subscription web application built on AWS as part of Cloud
Computing Assignment 2. Users can register, log in, search songs across a
DynamoDB dataset, and manage a personal subscription library. Artist images are
served from Amazon S3.

---

## Quick Start — Order of Operations

If you are setting this project up from scratch, follow every step in this exact order:

1. [Install prerequisites](#prerequisites)
2. [Configure the three required personal values](#before-you-start--required-configuration)
3. [Set up AWS credentials](#aws-credentials)
4. [Run the infrastructure scripts](#part-1--aws-infrastructure-setup) — DynamoDB + S3
5. Deploy a backend (pick one):
   - [EC2 Flask Backend](#part-2--ec2-flask-backend) ← Simplest to get running
   - [ECS Fargate](#part-3--ecs-fargate-backend)
   - [Lambda + API Gateway](#part-4--lambda--api-gateway-backend-recommended) ← Recommended for production
6. [Deploy the frontend](#part-5--frontend-deployment)
7. [Verify everything works](#part-6--end-to-end-verification)

---

## Project Structure

```
Cloud-A2-146/
│
├── data_setup/                         # One-time AWS infrastructure scripts
│   ├── config.py                       # Shared config: region, table names, bucket
│   ├── create_tables.py                # Creates login, music, subscriptions tables
│   ├── seed_login_table.py             # Inserts 10 seed login users
│   ├── load_music_table.py             # Loads 137 songs into DynamoDB
│   ├── upload_artist_images.py         # Downloads images → uploads to S3
│   ├── update_music_s3_keys.py         # Writes S3 image paths back to DynamoDB
│   ├── verify_system.py                # End-to-end test: login, query, subscribe
│   ├── bucket-policy.json              # S3 public read policy template
│   └── 2026a2_songs.json               # Source music dataset (137 songs)
│
├── backend_flask/                      # ✅ Complete — EC2 Flask backend
│   ├── app.py                          # Flask application and routes
│   ├── config.py                       # AWS constants
│   └── requirements.txt                # flask, flask-cors, boto3
│
├── ecs_backend/                        # ✅ Complete — Dockerised Flask app
│   ├── app.py                          # Flask application and routes
│   ├── config.py                       # AWS constants
│   ├── requirements.txt                # flask, flask-cors, boto3
│   └── Dockerfile                      # Container definition, runs Flask on port 80
│
├── lambda_backend/
│   ├── lambda_function.py              # ✅ Complete — single-file Lambda handler
│   └── template.yaml                   # SAM template — API Gateway + Lambda
│
└── frontend/                           # Static web UI — "Sonata"
    ├── login.html                      # Login page
    ├── register.html                   # Registration page
    ├── index.html                      # Main app — search and library
    ├── login.js                        # Login form logic
    ├── register.js                     # Registration form logic
    ├── app.js                          # All main frontend logic
    └── config.js                       # ← UPDATE API_BASE_URL HERE BEFORE DEPLOYING
```

---

## Prerequisites

Install all of the following before starting. Missing any single tool will cause
a specific part of the setup to fail.

### Required for everyone

| Tool | Minimum Version | Why It Is Needed | Install Link |
|------|----------------|------------------|--------------|
| Python | 3.10+ | Running all data setup scripts | [python.org](https://www.python.org/downloads/) |
| pip | Latest | Installing Python packages | Bundled with Python |
| AWS CLI v2 | 2.x | Configuring credentials, creating and managing all AWS resources from the terminal | [AWS CLI install guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |
| Git | Any | Cloning this repository | [git-scm.com](https://git-scm.com/) |

### Required for Lambda deployment

| Tool | Minimum Version | Why It Is Needed | Install Link |
|------|----------------|------------------|--------------|
| AWS SAM CLI | 1.100+ | Reads `template.yaml` to build and deploy the Lambda function and API Gateway as a single CloudFormation stack. Lambda cannot be deployed without this. | [SAM CLI install guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) |
| Docker Desktop | Latest | `sam build --use-container` packages your code inside a Docker container that mirrors the Lambda runtime environment exactly. SAM will refuse to build without Docker running. | [docker.com](https://www.docker.com/products/docker-desktop/) |

### Required for ECS deployment

| Tool | Minimum Version | Why It Is Needed | Install Link |
|------|----------------|------------------|--------------|
| Docker Desktop | Latest | Building the container image locally and pushing it to Amazon ECR | [docker.com](https://www.docker.com/products/docker-desktop/) |

### Verify your installs

Run all four commands and confirm each returns a version number before proceeding:

```bash
python --version      # Python 3.10.x or higher
aws --version         # aws-cli/2.x.x
sam --version         # SAM CLI, version 1.x.x  (Lambda path only)
docker --version      # Docker version xx.x      (Lambda and ECS paths)
```

### Install Python dependencies for the data setup scripts

Run this once from inside the `data_setup/` directory:

```bash
cd data_setup
pip install boto3 requests
```

---

## AWS Credentials

All scripts and backends authenticate with AWS using credentials stored in
`~/.aws/credentials`. AWS Academy credentials expire when your lab session ends
and must be refreshed at the start of every new session. Deploying with expired
credentials is the single most common cause of failures.

### Setting up credentials (first time or after expiry)

**Step 1.** Open your AWS Academy Lab and click **Start Lab**. Wait until the
dot next to "AWS" turns green.

**Step 2.** Click **AWS Details** in the top-right panel of the lab page, then
click **AWS CLI**.

**Step 3.** Click **Copy** on the credentials block — this copies all three lines.

**Step 4.** Open your credentials file and paste the copied block, replacing all
existing content:

- **Windows:** `C:\Users\<your-username>\.aws\credentials`
- **Mac / Linux:** `~/.aws/credentials`

The file must look exactly like this (your values will differ every session):

```ini
[default]
aws_access_key_id = ASIA...
aws_secret_access_key = wJalrXUtn...
aws_session_token = IQoJb3JpZ2...
```

**Step 5.** Verify the credentials are working before running anything else:

```bash
aws sts get-caller-identity
```

Expected output (your account ID and ARN will differ):

```json
{
    "UserId": "AROA...",
    "Account": "123456789012",
    "Arn": "arn:aws:sts::123456789012:assumed-role/vocstartsoft/user..."
}
```

If you see `ExpiredTokenException` or `InvalidClientTokenId`, the lab session
has expired — return to Step 1.

> **Important:** AWS Academy sessions typically last 4 hours. If you leave the
> project mid-way and return later, refresh your credentials before resuming.
> Any AWS CLI command or script run with expired credentials will fail.

---

## Before You Start — Required Configuration

Three values in the codebase are specific to your environment and **must be
updated before running any scripts or deploying any backend**. Skipping this
will either cause scripts to fail or insert incorrect seed data.

### 1. S3 bucket name

S3 bucket names are globally unique across all of AWS. Choose a name that is
unique to you (for example, `s1234567-music-images-2026`) and update it in all
three locations below. All three must be identical.

| File | Constant to update |
|------|--------------------|
| `data_setup/config.py` | `S3_BUCKET_NAME = "your-bucket-name"` |
| `ecs_backend/config.py` | `S3_BUCKET_NAME = "your-bucket-name"` |
| `lambda_backend/lambda_function.py` | `S3_BUCKET_NAME = "your-bucket-name"` |
| `backend_flask/config.py` | `S3_BUCKET_NAME = "your-bucket-name"` |

Also update `data_setup/bucket-policy.json` to use the same bucket name in the
`Resource` field:

```json
"Resource": "arn:aws:s3:::your-bucket-name/*"
```

### 2. Login seed user details

Open `data_setup/config.py` and update these two constants to reflect your own
student details before running `seed_login_table.py`:

```python
GROUP_BASE_STUDENT_ID = "s1234567"   # ← your actual RMIT student number
GROUP_BASE_NAME       = "GroupUser"  # ← display name prefix for the seed accounts
```

This generates 10 seed accounts that will be inserted into DynamoDB:

| Account | Email | Password |
|---------|-------|----------|
| 0 | s1234567+0@student.rmit.edu.au | 012345 |
| 1 | s1234567+1@student.rmit.edu.au | 123456 |
| 2 | s1234567+2@student.rmit.edu.au | 234567 |
| 3 | s1234567+3@student.rmit.edu.au | 345678 |
| 4 | s1234567+4@student.rmit.edu.au | 456789 |
| 5 | s1234567+5@student.rmit.edu.au | 567890 |
| 6 | s1234567+6@student.rmit.edu.au | 678901 |
| 7 | s1234567+7@student.rmit.edu.au | 789012 |
| 8 | s1234567+8@student.rmit.edu.au | 890123 |
| 9 | s1234567+9@student.rmit.edu.au | 901234 |

### 3. Frontend API URL

After deploying your chosen backend, you will receive a base URL. Open
`frontend/config.js` and update this line before deploying or testing the
frontend:

```javascript
// EC2 Flask backend:
const API_BASE_URL = "http://<ec2-public-ip>:5000";

// Lambda + API Gateway:
const API_BASE_URL = "https://<api-id>.execute-api.us-east-1.amazonaws.com/prod";

// ECS Fargate:
const API_BASE_URL = "http://<ecs-public-ip>";
```

---

## Part 1 — AWS Infrastructure Setup

These scripts are run **once** from your local machine to provision all required
AWS resources. Run them strictly in the order shown. All commands in this section
assume you are inside the `data_setup/` directory unless stated otherwise.

### Step 1.1 — Create the S3 bucket

This bucket stores all artist images served by the frontend.

```bash
# Create the bucket
# Note: us-east-1 does not require --create-bucket-configuration
aws s3api create-bucket \
  --bucket your-bucket-name \
  --region us-east-1

# Disable the default "block all public access" protection so images can be served publicly
aws s3api put-public-access-block \
  --bucket your-bucket-name \
  --public-access-block-configuration \
  "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"
```

Update `data_setup/bucket-policy.json` with your bucket name, then apply the policy:

```bash
aws s3api put-bucket-policy \
  --bucket your-bucket-name \
  --policy file://bucket-policy.json
```

Verify the bucket is accessible (no error = success; empty output is expected for a new bucket):

```bash
aws s3 ls s3://your-bucket-name
```

### Step 1.2 — Create the DynamoDB tables

```bash
cd data_setup
python create_tables.py
```

Expected output:

```
[INFO] Waiting for 'login' to become active...
[OK]   'login' is active and ready.
       Partition key → email

[INFO] Waiting for 'music' to become active...
[OK]   'music' is active and ready.
       Primary key  → title (PK) + artist#year (SK)
       GSI          → artist-index
       LSI          → title-year-index

[INFO] Waiting for 'subscriptions' to become active...
[OK]   'subscriptions' is active and ready.
       Partition key → email
       Sort key      → music_id

[DONE] All DynamoDB tables are ready.
```

If a table already exists from a previous run you will see:
`[SKIP] 'login' already exists — skipping creation.` — this is expected and safe.

**Verify in the AWS Console:** Navigate to **DynamoDB → Tables**. Confirm all
three tables show status **Active** before proceeding.

The complete table schemas created are:

| Table | Partition Key | Sort Key | Indexes |
|-------|--------------|----------|---------|
| `login` | `email` (String) | — | None |
| `music` | `title` (String) | `artist#year` (String) | GSI: `artist-index` on `artist` + `year`; LSI: `title-year-index` on `title` + `year` |
| `subscriptions` | `email` (String) | `music_id` (String) | None |

### Step 1.3 — Seed the login table

Confirm you have updated `GROUP_BASE_STUDENT_ID` and `GROUP_BASE_NAME` in
`config.py` before running this.

```bash
python seed_login_table.py
```

Expected output:

```
Successfully inserted 10 login records into the login table.

Inserted records:
{'email': 's1234567+0@student.rmit.edu.au', 'user_name': 'GroupUser0', 'password': '012345'}
{'email': 's1234567+1@student.rmit.edu.au', 'user_name': 'GroupUser1', 'password': '123456'}
...
{'email': 's1234567+9@student.rmit.edu.au', 'user_name': 'GroupUser9', 'password': '901234'}
```

**Verify in the AWS Console:** Navigate to **DynamoDB → Tables → login →
Explore table items** and confirm 10 records appear.

### Step 1.4 — Load the music table

```bash
python load_music_table.py
```

Expected output:

```
Loaded 137 songs from 2026a2_songs.json.

Successfully inserted 137 songs into the music table.
```

**Verify in the AWS Console:** Navigate to **DynamoDB → Tables → music →
Explore table items**. You should see 137 records.

### Step 1.5 — Upload artist images to S3

This script scans the music table for unique artist image URLs, downloads each
image from its source URL, and uploads it into the `artists/` prefix of your S3
bucket. A local `temp_images/` folder is created during this process and is
already excluded by `.gitignore`.

```bash
python upload_artist_images.py
```

Expected output:

```
Fetching unique images...
Found 67 unique images.

Uploaded: artists/TaylorSwift.jpg
Uploaded: artists/JackJohnson.jpg
Uploaded: artists/TheLumineers.jpg
...
All images processed.
```

This step takes approximately 1–3 minutes depending on your internet connection
speed. If an individual image fails to download, the remaining images continue
to be processed — the failure is non-fatal and that artist's songs will simply
display a placeholder icon in the UI.

**Verify in the AWS Console:** Navigate to **S3 → your-bucket-name → artists/**.
You should see approximately 67 `.jpg` files.

### Step 1.6 — Write S3 image keys back to DynamoDB

After images are uploaded, this script scans every song record in DynamoDB and
writes the corresponding S3 object key (for example, `artists/TaylorSwift.jpg`)
into the `image_s3_key` field. Without this step the backend has no path to
construct image URLs and all songs will render without images.

```bash
python update_music_s3_keys.py
```

Expected output:

```
Fetching all music items from DynamoDB...
Found 137 music items.

Updated: Love Story | Taylor Swift#2008 -> artists/TaylorSwift.jpg
Updated: Banana Pancakes | Jack Johnson#2005 -> artists/JackJohnson.jpg
...
Finished updating image_s3_key for all music items.
```

> **This step must be run after Step 1.5.** If you run the backends before
> completing this step, all songs will load correctly but images will be missing.

---

## Part 2 — EC2 Flask Backend

> ✅ This deployment path runs the Flask application directly on an Amazon EC2
> virtual machine. It is the most straightforward option to understand and debug,
> with no containerisation or serverless infrastructure required. The Flask API
> is served on port 5000 and the static frontend is served on port 8000, both
> from the same instance.

### Step 2.1 — Launch an EC2 instance

**2.1.1 — Open the EC2 Console**

In the AWS Management Console navigate to **EC2 → Instances → Launch instances**.

**2.1.2 — Configure the instance**

Fill in each section as follows:

| Setting | Value |
|---------|-------|
| Name | `sonata-backend` |
| Application and OS Images | **Amazon Linux 2023 AMI** (free tier eligible) |
| Instance type | **t3.micro** (free tier eligible) |
| Key pair | Select an existing key pair, or click **Create new key pair**, name it `sonata-key`, choose RSA and `.pem` format, then click **Create key pair** and save the downloaded `.pem` file somewhere safe — you cannot download it again |

**2.1.3 — Configure the security group**

Under **Network settings**, click **Edit** and configure inbound rules as follows.
Create a new security group named `sonata-sg` with the following three rules:

| Type | Protocol | Port range | Source | Description |
|------|----------|-----------|--------|-------------|
| SSH | TCP | 22 | My IP | Terminal access |
| Custom TCP | TCP | 5000 | Anywhere (0.0.0.0/0) | Flask backend API |
| Custom TCP | TCP | 8000 | Anywhere (0.0.0.0/0) | Frontend static file server |

**2.1.4 — Attach the IAM instance profile**

Expand **Advanced details** and locate the **IAM instance profile** dropdown.
Select **LabRole** from the list. This grants the instance permission to access
DynamoDB and S3 without embedding credentials in the code.

**2.1.5 — Launch the instance**

Leave all remaining settings at their defaults and click **Launch instance**.
Wait approximately 2 minutes for the instance state to show **Running** and the
status checks to show **2/2 checks passed** before proceeding.

**2.1.6 — Note the public IP address**

In the EC2 Console click on your instance and copy the **Public IPv4 address**
displayed in the instance summary panel. You will need this in subsequent steps.

### Step 2.2 — Prepare your SSH key

Before connecting, the `.pem` key file must have restricted permissions.
Skip this step on Windows — PowerShell handles permissions differently.

**Linux / Mac:**

```bash
chmod 400 /path/to/sonata-key.pem
```

### Step 2.3 — Upload the backend files to the instance

Upload the entire `backend_flask/` directory from your local machine to the EC2
instance using `scp`. Replace `<EC2_PUBLIC_IP>` with your instance's actual public
IP and adjust the path to your `.pem` file as needed.

**Linux / Mac:**

```bash
scp -i /path/to/sonata-key.pem -r backend_flask/ \
  ec2-user@<EC2_PUBLIC_IP>:~/backend_flask
```

**Windows PowerShell:**

```powershell
scp -i C:\path\to\sonata-key.pem -r backend_flask/ `
  ec2-user@<EC2_PUBLIC_IP>:~/backend_flask
```

Expected output — you will see a progress line for each file transferred:

```
app.py                  100%  4321     1.2MB/s   00:00
config.py               100%   312   450.0KB/s   00:00
requirements.txt        100%    27   150.0KB/s   00:00
```

### Step 2.4 — Upload the frontend files to the instance

Upload the entire `frontend/` directory in the same way. Make sure you have
already updated `frontend/config.js` with `http://<EC2_PUBLIC_IP>:5000` before
uploading.

**Linux / Mac:**

```bash
scp -i /path/to/sonata-key.pem -r frontend/ \
  ec2-user@<EC2_PUBLIC_IP>:~/frontend
```

**Windows PowerShell:**

```powershell
scp -i C:\path\to\sonata-key.pem -r frontend/ `
  ec2-user@<EC2_PUBLIC_IP>:~/frontend
```

### Step 2.5 — Connect to the instance via SSH

**Linux / Mac:**

```bash
ssh -i /path/to/sonata-key.pem ec2-user@<EC2_PUBLIC_IP>
```

**Windows PowerShell:**

```powershell
ssh -i C:\path\to\sonata-key.pem ec2-user@<EC2_PUBLIC_IP>
```

You are now logged into the instance. All subsequent commands in this section
are run inside this SSH session.

### Step 2.6 — Install Python dependencies on the instance

```bash
# Update system packages
sudo dnf update -y

# Install pip if not already present
sudo dnf install -y python3-pip

# Navigate to the backend directory
cd ~/backend_flask

# Install required Python packages
pip3 install flask flask-cors boto3
```

Verify the installation completed without errors:

```bash
python3 -c "import flask, boto3; print('Dependencies installed successfully')"
```

### Step 2.7 — Start the Flask backend

Run the Flask application in the background so it keeps running after you close
the terminal:

```bash
cd ~/backend_flask
nohup python3 app.py > ~/flask.log 2>&1 &
echo "Flask started. PID: $!"
```

Confirm the server is listening on port 5000:

```bash
curl http://localhost:5000/
```

Expected response:

```json
{"message": "AWS Music Subscription Backend is running"}
```

To check the Flask log at any time:

```bash
tail -f ~/flask.log
```

### Step 2.8 — Start the frontend file server

Serve the static frontend files using Python's built-in HTTP server on port 8000:

```bash
cd ~/frontend
nohup python3 -m http.server 8000 > ~/frontend.log 2>&1 &
echo "Frontend server started on port 8000."
```

### Step 2.9 — Access the live application

Your application is now accessible at the following URLs. Replace `<EC2_PUBLIC_IP>`
with your instance's public IP address:

| Service | URL |
|---------|-----|
| Frontend (login page) | `http://<EC2_PUBLIC_IP>:8000/login.html` |
| Backend API (health check) | `http://<EC2_PUBLIC_IP>:5000/` |

Open the frontend URL in your browser to begin testing.

### Step 2.10 — Smoke test the live API

Run these commands from your **local** terminal (not inside the SSH session)
to confirm the API is accessible from the public internet:

**Linux / Mac:**

```bash
export EC2="http://<EC2_PUBLIC_IP>:5000"

# Health check
curl $EC2/

# Login with a seed user
curl -s -X POST $EC2/login \
  -H "Content-Type: application/json" \
  -d '{"email":"s1234567+0@student.rmit.edu.au","password":"012345"}'

# Query songs by artist
curl -s "$EC2/songs?artist=Taylor+Swift"
```

**Windows PowerShell:**

```powershell
$EC2 = "http://<EC2_PUBLIC_IP>:5000"

# Health check
Invoke-RestMethod -Uri "$EC2/"

# Login
Invoke-RestMethod -Method POST -Uri "$EC2/login" `
  -ContentType "application/json" `
  -Body '{"email":"s1234567+0@student.rmit.edu.au","password":"012345"}'

# Song query
Invoke-RestMethod -Uri "$EC2/songs?artist=Taylor Swift"
```

A `{"success": true}` login response and a `songs` array from the query confirm
the backend is fully operational and communicating with DynamoDB.

### Stopping the EC2 servers

To stop both processes running on the instance:

```bash
# Stop Flask backend
pkill -f "python3 app.py"

# Stop frontend file server
pkill -f "http.server 8000"
```

To restart them after a reboot, repeat Steps 2.7 and 2.8.

### Re-uploading files after changes

If you modify any backend or frontend file locally, re-upload only the changed
files using `scp` with the individual file path instead of the directory:

```bash
# Re-upload a single file
scp -i /path/to/sonata-key.pem backend_flask/app.py \
  ec2-user@<EC2_PUBLIC_IP>:~/backend_flask/app.py

# Then restart Flask on the instance
ssh -i /path/to/sonata-key.pem ec2-user@<EC2_PUBLIC_IP> \
  "pkill -f 'python3 app.py'; cd ~/backend_flask && nohup python3 app.py > ~/flask.log 2>&1 &"
```

---

## Part 3 — ECS Fargate Backend

> ✅ The ECS backend (`ecs_backend/`) is complete. This deployment path runs the
> Flask application inside a Docker container on AWS Fargate, a serverless
> container runtime that requires no EC2 instance management.

### Before starting Part 3 — Pre-requirements checklist

Complete every item in this checklist **before** running Step 3.1. Skipping any
item will cause a specific step to fail and is the most common source of errors
in the ECS deployment path.

**1. Docker Desktop is installed and fully running**

Open Docker Desktop from your Applications or Start menu. Wait until the whale
icon in the system tray stops animating and shows "Docker Desktop is running."
Then confirm Docker responds:

```bash
docker info
```

If this prints engine details, Docker is ready. If it returns an error such as
`Cannot connect to the Docker daemon`, Docker has not finished starting — wait
another 30 seconds and retry. Do not proceed to Step 3.1 until this command
succeeds.

**2. AWS CLI v2 is installed and credentials are valid (not expired)**

```bash
aws sts get-caller-identity
```

This must return your account ID and ARN. If you see `ExpiredTokenException`,
refresh your credentials from the AWS Academy portal before continuing. See the
[AWS Credentials section](#aws-credentials) for the full refresh procedure.

**3. Your AWS account ID is noted**

The ECS task definition requires your 12-digit account ID in two places. Retrieve
it now and keep it handy:

```bash
aws sts get-caller-identity --query Account --output text
```

**4. Part 1 infrastructure is fully complete**

All six Part 1 steps must be finished before ECS can serve data. Verify:

```bash
# All three tables should show ACTIVE
aws dynamodb list-tables --query "TableNames"

# The music table should have 137 items
aws dynamodb scan --table-name music --select COUNT --query "Count"

# The artists/ prefix should contain roughly 67 images
aws s3 ls s3://your-bucket-name/artists/ | wc -l
```

If any of these checks fails, return to Part 1 and complete the missing steps
before continuing.

**5. Your S3 bucket name is updated in `ecs_backend/config.py`**

Open `ecs_backend/config.py` and confirm `S3_BUCKET_NAME` matches the bucket
you created in Step 1.1. If it still contains the placeholder value, update it
now before building the Docker image — the bucket name is baked into the image
at build time.

**6. Internet access is available for the ECR image pull**

The Fargate task pulls the image from ECR at launch time. Confirm that your
chosen subnet has internet access (the default VPC's default subnets do). If
you are using a custom VPC, ensure there is an internet gateway and the subnet's
route table sends `0.0.0.0/0` traffic to it.

---

### Step 3.1 — Create an ECR repository

Amazon ECR (Elastic Container Registry) is where your Docker image is stored
so ECS can pull it when launching tasks.

```bash
aws ecr create-repository \
  --repository-name music-subscription-api \
  --region us-east-1
```

From the JSON output, note the `repositoryUri` value:

```
123456789012.dkr.ecr.us-east-1.amazonaws.com/music-subscription-api
```

Store it in a variable for use in subsequent commands:

```bash
# Linux / Mac
export ECR_URI="123456789012.dkr.ecr.us-east-1.amazonaws.com/music-subscription-api"

# Windows PowerShell
$ECR_URI = "123456789012.dkr.ecr.us-east-1.amazonaws.com/music-subscription-api"
```

### Step 3.2 — Build and push the Docker image

```bash
cd ecs_backend

# Step A — Authenticate Docker to your ECR registry
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.us-east-1.amazonaws.com

# Step B — Build the container image from the Dockerfile
docker build -t music-subscription-api .

# Step C — Tag the image with your ECR repository URI
docker tag music-subscription-api:latest $ECR_URI:latest

# Step D — Push the image to ECR
docker push $ECR_URI:latest
```

Verify the image was pushed successfully:

```bash
aws ecr list-images --repository-name music-subscription-api
```

The output should show one image with tag `latest`.

### Step 3.3 — Create the ECS cluster and CloudWatch log group

```bash
# Create the ECS cluster
aws ecs create-cluster --cluster-name music-app-cluster

# Create the log group so container logs are captured from the start
aws logs create-log-group --log-group-name /ecs/music-subscription
```

### Step 3.4 — Register the ECS task definition

Create a file named `task-def.json` in your current directory. Replace both
occurrences of `<YOUR_ACCOUNT_ID>` and update the ECR image URI with your own.
The task and execution roles are both set to `LabRole`, which already has the
required DynamoDB and S3 permissions attached.

```json
{
  "family": "music-subscription-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::<YOUR_ACCOUNT_ID>:role/LabRole",
  "taskRoleArn": "arn:aws:iam::<YOUR_ACCOUNT_ID>:role/LabRole",
  "containerDefinitions": [
    {
      "name": "music-api",
      "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/music-subscription-api:latest",
      "portMappings": [
        { "containerPort": 80, "protocol": "tcp" }
      ],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/music-subscription",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

Register the task definition:

```bash
aws ecs register-task-definition --cli-input-json file://task-def.json
```

Confirm registration:

```bash
aws ecs list-task-definitions
```

You should see `music-subscription-task:1` in the output.

### Step 3.5 — Identify your default VPC and a public subnet

Fargate tasks launched with a public IP must be placed in a public subnet. Use
the default VPC for simplicity.

```bash
# Get your default VPC ID
VPC_ID=$(aws ec2 describe-vpcs \
  --filters Name=isDefault,Values=true \
  --query "Vpcs[0].VpcId" --output text)
echo "Default VPC: $VPC_ID"

# Get a public subnet in the default VPC
SUBNET_ID=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=defaultForAz,Values=true" \
  --query "Subnets[0].SubnetId" --output text)
echo "Public Subnet: $SUBNET_ID"
```

### Step 3.6 — Create a security group and open port 80

```bash
# Create the security group
SG_ID=$(aws ec2 create-security-group \
  --group-name music-api-sg \
  --description "Allow inbound HTTP for Sonata music API" \
  --vpc-id $VPC_ID \
  --query "GroupId" --output text)
echo "Security Group ID: $SG_ID"

# Allow inbound HTTP traffic on port 80 from any source
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0
```

### Step 3.7 — Create the ECS service and launch the container

```bash
aws ecs create-service \
  --cluster music-app-cluster \
  --service-name music-api-service \
  --task-definition music-subscription-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration \
    "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SG_ID],assignPublicIp=ENABLED}"
```

Wait for the service to reach a stable running state (this may take up to 5
minutes while AWS pulls the image and starts the container):

```bash
aws ecs wait services-stable \
  --cluster music-app-cluster \
  --services music-api-service

echo "ECS service is stable and running."
```

### Step 3.8 — Retrieve the container's public IP address

```bash
# Get the ARN of the running task
TASK_ARN=$(aws ecs list-tasks \
  --cluster music-app-cluster \
  --service-name music-api-service \
  --query "taskArns[0]" --output text)
echo "Task ARN: $TASK_ARN"

# Get the Elastic Network Interface ID attached to the task
ENI_ID=$(aws ecs describe-tasks \
  --cluster music-app-cluster \
  --tasks $TASK_ARN \
  --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" \
  --output text)
echo "Network Interface ID: $ENI_ID"

# Get the public IP address assigned to that network interface
PUBLIC_IP=$(aws ec2 describe-network-interfaces \
  --network-interface-ids $ENI_ID \
  --query "NetworkInterfaces[0].Association.PublicIp" \
  --output text)
echo "ECS Public IP: $PUBLIC_IP"
```

### Step 3.9 — Update the frontend config and smoke test

Open `frontend/config.js`:

```javascript
const API_BASE_URL = "http://<your-ecs-public-ip>";
```

Run a quick smoke test to confirm the container is serving requests:

```bash
# Health check
curl http://$PUBLIC_IP/

# Login test
curl -s -X POST http://$PUBLIC_IP/login \
  -H "Content-Type: application/json" \
  -d '{"email":"s1234567+0@student.rmit.edu.au","password":"012345"}'
```

Both commands should return valid JSON. A `{"success": true}` login response
confirms the container can reach DynamoDB successfully.

---

## Part 4 — Lambda + API Gateway Backend (Recommended)

> ✅ This is the recommended and complete deployment path. A single Lambda
> function handles all application routes. API Gateway exposes a secure HTTPS
> endpoint. There are no servers to manage and AWS handles all scaling automatically.

### Before starting Part 4 — Pre-requirements checklist

Complete every item in this checklist **before** running Step 4.3. Each item
maps to a specific failure mode if skipped.

**1. Docker Desktop is installed and fully running**

SAM CLI builds the Lambda package inside a Docker container that replicates
the Lambda runtime environment. Without Docker running, `sam build` exits
immediately with `Error: Docker is not reachable`.

Open Docker Desktop and wait until the whale icon in the system tray stops
animating, then confirm:

```bash
docker info
```

This must print engine details — any error means Docker is not yet ready.
Do not run `sam build` until this command succeeds.

**2. AWS SAM CLI is installed**

```bash
sam --version
```

This must print a version number such as `SAM CLI, version 1.x.x`. If the
command is not found, install SAM CLI from the
[official guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
before continuing.

**3. AWS CLI v2 is installed and credentials are valid (not expired)**

```bash
aws sts get-caller-identity
```

This must return your account ID and ARN. If you see `ExpiredTokenException`,
refresh your credentials from the AWS Academy portal before continuing. Expired
credentials during `sam deploy` will leave a CloudFormation stack in a
`ROLLBACK_COMPLETE` state that must be manually deleted before you can redeploy.
See the [AWS Credentials section](#aws-credentials) for the full refresh procedure.

**4. Your LabRole ARN is noted**

Lambda functions in AWS Academy must be assigned the pre-created `LabRole` IAM
role. You cannot create new IAM roles. Retrieve the ARN now:

1. In the AWS Console navigate to **IAM → Roles**
2. Search for `LabRole` and click on it
3. Copy the **ARN** shown at the top — it follows this format:
   `arn:aws:iam::123456789012:role/LabRole`

You can also retrieve it with the CLI:

```bash
aws iam get-role --role-name LabRole --query "Role.Arn" --output text
```

Keep this value available — you pass it as a parameter in Step 4.4.

**5. Part 1 infrastructure is fully complete**

All six Part 1 steps must be finished before Lambda can serve data. Verify:

```bash
# All three tables should appear
aws dynamodb list-tables --query "TableNames"

# The music table should have 137 items
aws dynamodb scan --table-name music --select COUNT --query "Count"

# The artists/ prefix should contain roughly 67 images
aws s3 ls s3://your-bucket-name/artists/ | wc -l
```

If any of these checks fails, return to Part 1 and complete the missing steps
before continuing.

**6. Your S3 bucket name is updated in `lambda_backend/lambda_function.py`**

Open `lambda_backend/lambda_function.py` and confirm the `S3_BUCKET_NAME`
constant at the top of the file matches the bucket you created in Step 1.1.
This value is packaged into the Lambda ZIP at build time. Deploying with the
wrong bucket name means all song images will return empty URLs.

**7. Both required files are present in `lambda_backend/`**

```bash
ls lambda_backend/
```

You must see both `lambda_function.py` and `template.yaml`. If either is
missing, restore it from version control before running `sam build`.

**8. No existing failed CloudFormation stack with the same name**

If a previous `sam deploy` attempt failed, AWS may have left a stack in
`ROLLBACK_COMPLETE` state. A stack in this state blocks all future deployments
with the same name. Check and delete it if necessary:

```bash
aws cloudformation describe-stacks \
  --stack-name music-subscription-lambda \
  --query "Stacks[0].StackStatus" --output text
```

If the output is `ROLLBACK_COMPLETE`, delete the stack before retrying:

```bash
aws cloudformation delete-stack --stack-name music-subscription-lambda
aws cloudformation wait stack-delete-complete --stack-name music-subscription-lambda
echo "Stack deleted. Safe to redeploy."
```

---

### Step 4.1 — Confirm the Lambda files are in place

Your `lambda_backend/` folder must contain both of these files:

```
lambda_backend/
├── lambda_function.py   # Application handler — all routes implemented
└── template.yaml        # SAM deployment template — defines API Gateway + Lambda
```

No `requirements.txt` is needed. `boto3` is pre-installed in the Lambda Python
runtime and no additional dependencies are required.

### Step 4.2 — Get your LabRole ARN

Lambda functions deployed in AWS Academy must be assigned the pre-created
`LabRole` IAM role. You cannot create new IAM roles in Academy accounts.

1. In the AWS Console navigate to **IAM → Roles**
2. Search for `LabRole` and click on it
3. Copy the **ARN** displayed at the top of the page

The ARN follows this format:

```
arn:aws:iam::123456789012:role/LabRole
```

Keep this value available — you will pass it as a parameter in Step 4.3.

To retrieve your account ID separately:

```bash
aws sts get-caller-identity --query Account --output text
```

### Step 4.3 — Build the Lambda deployment package

SAM packages your application code inside a Docker container that replicates
the Lambda runtime environment. This ensures the package is compatible with
the live Lambda execution environment. Docker Desktop must be running before
executing this command.

```bash
cd lambda_backend
sam build --use-container
```

Expected output:

```
Building codeuri: . runtime: python3.10 metadata: {} architecture: x86_64
Running PythonPipBuilder:ResolveDependencies
Running PythonPipBuilder:CopySource

Build Succeeded

Built Artifacts  : .aws-sam/build
Built Template   : .aws-sam/build/template.yaml
```

> If `sam build` fails with `Error: Docker is not reachable`, Docker Desktop
> has not finished starting. Wait until the whale icon in the system tray stops
> animating, then retry.

### Step 4.4 — Deploy to AWS (first time — guided wizard)

```bash
sam deploy --guided \
  --parameter-overrides LabRoleArn=arn:aws:iam::<YOUR_ACCOUNT_ID>:role/LabRole
```

Replace `<YOUR_ACCOUNT_ID>` with your actual 12-digit AWS account ID.

The wizard will prompt you with a series of configuration questions. Answer them
exactly as shown in the table below:

| Prompt | Answer |
|--------|--------|
| Stack Name [sam-app] | `music-subscription-lambda` |
| AWS Region [us-east-1] | Press **Enter** to accept |
| Parameter LabRoleArn | Paste your full LabRole ARN |
| Confirm changes before deploy [Y/n] | `y` |
| Allow SAM CLI IAM role creation [Y/n] | `n` |
| Disable rollback [y/N] | `n` |
| `MusicSubscriptionFunction` may not have authorization defined, Is this okay? [y/N] | `y` — repeat this for each of the approximately 11 route prompts |
| Save arguments to configuration file [Y/n] | `y` |
| SAM configuration file [samconfig.toml] | Press **Enter** to accept |
| SAM configuration environment [default] | Press **Enter** to accept |

SAM will display a changeset preview listing every AWS resource it will create
— the Lambda function, API Gateway, all routes, CloudWatch log group, and IAM
bindings. When asked `Deploy this changeset? [y/N]` type `y`.

Deployment takes approximately 1–3 minutes. On success you will see:

```
Successfully created/updated stack - music-subscription-lambda in us-east-1
```

### Step 4.5 — Retrieve your API URL

Immediately after a successful deployment SAM prints an Outputs table to the
terminal:

```
------------------------------------------------------------------------------------
Outputs
------------------------------------------------------------------------------------
Key         ApiBaseUrl
Description Live API Gateway base URL — paste this into frontend/config.js
Value       https://nsf6ua05d6.execute-api.us-east-1.amazonaws.com/prod
------------------------------------------------------------------------------------
```

Copy the `Value`. If you need to retrieve it later at any time:

```bash
aws cloudformation describe-stacks \
  --stack-name music-subscription-lambda \
  --query "Stacks[0].Outputs[?OutputKey=='ApiBaseUrl'].OutputValue" \
  --output text
```

### Step 4.6 — Update the frontend config

Open `frontend/config.js` and set your API base URL:

```javascript
const API_BASE_URL = "https://nsf6ua05d6.execute-api.us-east-1.amazonaws.com/prod";
```

### Step 4.7 — Smoke test the live API

Run a quick set of manual tests to confirm the deployed API is responding
correctly before deploying the frontend.

**Linux / Mac:**

```bash
export API="https://nsf6ua05d6.execute-api.us-east-1.amazonaws.com/prod"

# Health check
curl $API/

# Login with a seed user
curl -s -X POST $API/login \
  -H "Content-Type: application/json" \
  -d '{"email":"s1234567+0@student.rmit.edu.au","password":"012345"}'

# Query songs by artist
curl -s "$API/songs?artist=Taylor+Swift"
```

**Windows PowerShell:**

```powershell
$API = "https://nsf6ua05d6.execute-api.us-east-1.amazonaws.com/prod"

# Health check
Invoke-RestMethod -Uri "$API/"

# Login
Invoke-RestMethod -Method POST -Uri "$API/login" `
  -ContentType "application/json" `
  -Body '{"email":"s1234567+0@student.rmit.edu.au","password":"012345"}'

# Song query
Invoke-RestMethod -Uri "$API/songs?artist=Taylor Swift"
```

All three commands should return valid JSON responses. If the login returns
`{"success": true}` and the song query returns a `songs` array, the backend is
fully operational.

### Step 4.8 — Subsequent deploys after code changes

After the first deployment, SAM saves all your configuration to `samconfig.toml`
in the `lambda_backend/` directory. All future deploys after code changes are
a single command with no interactive prompts:

```bash
sam build --use-container && sam deploy
```

### Tear down the Lambda stack

To remove all Lambda and API Gateway resources when no longer needed:

```bash
sam delete --stack-name music-subscription-lambda
```

This removes the Lambda function, API Gateway, and CloudFormation stack.
DynamoDB tables and the S3 bucket are **not** deleted as they are shared
infrastructure.

---

## Part 5 — Frontend Deployment

The Sonata frontend is a set of static HTML, CSS, and JavaScript files that
require no server-side rendering. The recommended hosting method is Amazon S3
static website hosting.

### Option A — S3 Static Website Hosting (Recommended)

Before uploading any files, confirm that `frontend/config.js` has been updated
with the correct `API_BASE_URL` for your deployed backend.

**Step 5A.1 — Create a dedicated frontend S3 bucket**

This must be a separate bucket from your images bucket:

```bash
aws s3api create-bucket \
  --bucket sonata-frontend-<your-student-id> \
  --region us-east-1
```

**Step 5A.2 — Enable static website hosting**

```bash
aws s3 website s3://sonata-frontend-<your-student-id>/ \
  --index-document login.html \
  --error-document login.html
```

**Step 5A.3 — Make the bucket publicly readable**

```bash
# Disable the block public access setting
aws s3api put-public-access-block \
  --bucket sonata-frontend-<your-student-id> \
  --public-access-block-configuration \
  "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"
```

Create `frontend-policy.json` (replace the bucket name):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::sonata-frontend-<your-student-id>/*"
    }
  ]
}
```

Apply the policy:

```bash
aws s3api put-bucket-policy \
  --bucket sonata-frontend-<your-student-id> \
  --policy file://frontend-policy.json
```

**Step 5A.4 — Upload all frontend files**

```bash
aws s3 sync frontend/ s3://sonata-frontend-<your-student-id>/
```

**Step 5A.5 — Access the live application**

Your application is now publicly available at:

```
http://sonata-frontend-<your-student-id>.s3-website-us-east-1.amazonaws.com/login.html
```

To update the frontend after any changes, re-run the sync command:

```bash
aws s3 sync frontend/ s3://sonata-frontend-<your-student-id>/
```

### Option B — EC2-hosted frontend (Part 2 path only)

If you deployed the EC2 backend in Part 2, the frontend is already being served
from port 8000 of the same instance. No additional setup is required — simply
open `http://<EC2_PUBLIC_IP>:8000/login.html` in your browser. To update after
changes, re-upload the modified files via `scp` as described in Step 2.4.

### Option C — Open locally (development and quick testing only)

Open `frontend/login.html` directly in your browser. Since `config.js` points
to a live URL, the frontend connects to your deployed backend without requiring
a local web server. This method is suitable for rapid testing but not for
submission or sharing.

---

## Part 6 — End-to-End Verification

### Automated DynamoDB verification script

This script directly exercises all five core operations — login lookup, music
query, add subscription, view subscriptions, and remove subscription — against
your live DynamoDB tables without going through the API.

```bash
cd data_setup
python verify_system.py
```

All five tests passing confirms your DynamoDB tables, credentials, and data
setup are fully operational:

```
--- TEST 1: LOGIN ---
Login user found: GroupUser0

--- TEST 2: MUSIC QUERY (Artist) ---
Found 7 songs for Taylor Swift
- Bad Blood (2014)
- Delicate (2017)
- I Knew You Were Trouble (2012)

--- TEST 3: ADD SUBSCRIPTION ---
Subscribed to: 1904

--- TEST 4: VIEW SUBSCRIPTIONS ---
Total subscriptions: 1
- 1904 (The Tallest Man on Earth)

--- TEST 5: REMOVE SUBSCRIPTION ---
Removed: 1904

--- TEST 4: VIEW SUBSCRIPTIONS ---
Total subscriptions: 0
```

### Manual browser test

Perform the following steps in the browser to confirm the full end-to-end
application flow is working:

1. Open the frontend URL (or `login.html` locally)
2. Log in with a seed account, for example `s1234567+0@student.rmit.edu.au` / `012345`
3. Confirm you are redirected to `index.html` and the My Library section shows
   as empty with a "Your library is empty" message
4. In the search bar, type `Taylor Swift` in the Artist field and click Search
5. Confirm at least 7 song cards appear with artist images loaded from S3
6. Click **+ Subscribe** on any song — confirm it immediately appears in My Library
7. Click **✕ Remove** on the subscribed song — confirm it disappears from My Library
8. Click **Sign Out** — confirm you are redirected back to the login page

---

## API Reference

Base URL (EC2): `http://<ec2-public-ip>:5000`

Base URL (ECS): `http://<ecs-public-ip>`

Base URL (Lambda): `https://<api-id>.execute-api.us-east-1.amazonaws.com/prod`

All endpoints accept and return `application/json`. The `music_id` composite
key format used for subscription operations is: `{artist}#{title}#{year}#{album}`

---

### GET `/`
Health check endpoint.

**Response 200:**
```json
{ "message": "AWS Music Subscription Backend is running" }
```

---

### POST `/login`

**Request body:**
```json
{ "email": "s1234567+0@student.rmit.edu.au", "password": "012345" }
```

**Response 200 — success:**
```json
{ "success": true, "message": "login successful", "user_name": "GroupUser0", "email": "s1234567+0@student.rmit.edu.au" }
```

**Response 400 — missing fields:**
```json
{ "success": false, "message": "email or password is invalid" }
```

**Response 401 — invalid credentials:**
```json
{ "success": false, "message": "email or password is invalid" }
```

---

### POST `/register`

**Request body:**
```json
{ "email": "newuser@example.com", "user_name": "Alice", "password": "mypassword" }
```

**Response 201 — success:**
```json
{ "success": true, "message": "registration successful" }
```

**Response 400 — missing fields:**
```json
{ "success": false, "message": "missing required fields" }
```

**Response 409 — email already registered:**
```json
{ "success": false, "message": "The email already exists" }
```

---

### GET `/songs`

At least one query parameter is required. Multiple parameters are combined with
AND logic — only songs matching all supplied filters are returned.

**Query parameters:** `title`, `artist`, `year`, `album`

```
GET /songs?artist=Taylor+Swift
GET /songs?artist=Taylor+Swift&album=Fearless
GET /songs?title=Hotel+California
GET /songs?year=1977
GET /songs?title=Bad+Blood&artist=Taylor+Swift
```

**Response 200 — results found:**
```json
{
  "success": true,
  "message": "songs retrieved successfully",
  "songs": [
    {
      "title": "Love Story",
      "artist": "Taylor Swift",
      "year": "2008",
      "album": "Fearless",
      "image_url": "https://your-bucket.s3.amazonaws.com/artists/TaylorSwift.jpg",
      "image_s3_key": "artists/TaylorSwift.jpg"
    }
  ]
}
```

**Response 200 — no matching results:**
```json
{ "success": true, "message": "No result is retrieved. Please query again", "songs": [] }
```

**Response 400 — no query parameters supplied:**
```json
{ "success": false, "message": "At least one query field is required", "songs": [] }
```

---

### GET `/subscriptions`

**Query parameter:** `email` (required)

```
GET /subscriptions?email=s1234567%2B0%40student.rmit.edu.au
```

**Response 200:**
```json
{ "success": true, "subscriptions": [ { "title": "...", "artist": "...", "year": "...", "album": "...", "music_id": "...", "image_url": "..." } ] }
```

---

### POST `/subscriptions`

**Request body:**
```json
{
  "email": "s1234567+0@student.rmit.edu.au",
  "title": "Love Story",
  "artist": "Taylor Swift",
  "year": "2008",
  "album": "Fearless",
  "image_s3_key": "artists/TaylorSwift.jpg"
}
```

**Response 201:**
```json
{ "success": true, "message": "subscription added successfully" }
```

---

### DELETE `/subscriptions`

**Request body:**
```json
{
  "email": "s1234567+0@student.rmit.edu.au",
  "music_id": "Taylor Swift#Love Story#2008#Fearless"
}
```

**Response 200:**
```json
{ "success": true, "message": "subscription removed successfully" }
```

---

## Troubleshooting

### `NoCredentialsError` or `ExpiredTokenException`
Your AWS Academy lab session has expired. Return to the AWS Academy portal,
click Start Lab, copy the new credentials from AWS Details → AWS CLI, and paste
them into `~/.aws/credentials`. Run `aws sts get-caller-identity` to confirm
the new credentials are working before retrying.

---

### `ResourceNotFoundException: Requested resource not found`
The DynamoDB table referenced does not exist. Run `python create_tables.py`
from the `data_setup/` directory. If tables already exist but the error
persists, confirm that `AWS_REGION` in `data_setup/config.py` is `us-east-1`
and that you are querying the correct AWS account.

---

### Images not loading in the frontend
Work through the following checklist in order:

1. Confirm `upload_artist_images.py` completed without errors and that files appear in your S3 bucket under the `artists/` prefix
2. Confirm `update_music_s3_keys.py` was run **after** the upload script — if skipped, `image_s3_key` remains empty in DynamoDB and no URL can be constructed
3. In the AWS Console go to **S3 → your bucket → Permissions** and confirm that "Block all public access" shows **Off**
4. Confirm the bucket policy is present under **Permissions → Bucket policy** and shows `s3:GetObject` with `Principal: "*"`
5. Test one image URL directly in your browser: `https://your-bucket-name.s3.amazonaws.com/artists/TaylorSwift.jpg`

---

### EC2 Flask server not responding

If the API is unreachable from your browser or `curl`:

1. Confirm the Flask process is still running on the instance: `ssh` in and run `ps aux | grep python3`
2. If the process has stopped, restart it with `cd ~/backend_flask && nohup python3 app.py > ~/flask.log 2>&1 &`
3. Confirm the security group has an inbound rule allowing TCP on port 5000 from `0.0.0.0/0` — navigate to **EC2 → Security Groups → sonata-sg → Inbound rules**
4. Confirm the instance has a public IP and has not been stopped — navigate to **EC2 → Instances** and check the **Instance state** and **Public IPv4 address** columns
5. Check the Flask log for Python exceptions: `tail -50 ~/flask.log`

---

### EC2 `Permission denied (publickey)` on SSH or SCP
The `.pem` key file permissions are too open. On Linux and Mac run:

```bash
chmod 400 /path/to/sonata-key.pem
```

Then retry the `ssh` or `scp` command. On Windows this error usually means the
wrong key file is being specified — confirm the path in your command exactly
matches where the `.pem` was saved when downloaded.

---

### Lambda returns `{"message": "Internal Server Error"}`
API Gateway returns this generic message when the Lambda function throws an
uncaught Python exception. To find the actual error:

1. Go to **CloudWatch → Log groups → /aws/lambda/music-subscription-handler**
2. Open the most recent log stream
3. Find the line beginning with `[ERROR]` — it shows the complete Python traceback

Common causes and fixes:

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `AccessDeniedException` in the traceback | Lambda execution role missing DynamoDB permissions | Confirm LabRole is attached to the Lambda function in the SAM template |
| `ResourceNotFoundException` in the traceback | Table name in `lambda_function.py` doesn't match what was created | Confirm `LOGIN_TABLE`, `MUSIC_TABLE`, `SUBSCRIPTIONS_TABLE` constants match the actual DynamoDB table names |
| `ExpiredTokenException` in the traceback | Lab session expired mid-deployment | Refresh credentials and redeploy: `sam build --use-container && sam deploy` |

---

### `AccessDeniedException` on all ECS API calls
Confirm that `LabRole` is specified as both the `executionRoleArn` and `taskRoleArn`
in `task-def.json`, then force a new task deployment to pick up the updated role:

```bash
aws ecs update-service \
  --cluster music-app-cluster \
  --service music-api-service \
  --force-new-deployment
```

---

### ECS task stays in PENDING or keeps restarting
Check CloudWatch Logs at `/ecs/music-subscription` for the container crash
reason. Common causes:

- ECR image URI in `task-def.json` contains a typo — verify the account ID, region, and repository name exactly
- Security group does not allow inbound TCP on port 80 — verify the inbound rule is present
- Subnet has no internet gateway — the Fargate task needs internet access both to pull the ECR image and to call DynamoDB; ensure the subnet is public and `assignPublicIp` is `ENABLED`

---

### `sam build` fails with `Error: Docker is not reachable`
Docker Desktop has not finished starting. Open it from your Applications or
Start menu, wait until the whale icon in the system tray stops animating and
shows "Docker Desktop is running", then retry `sam build --use-container`.

---

### `sam deploy` fails with `No changes to deploy`
SAM detected that the built template and code are identical to the last
deployed version. If you made code changes and still see this message, force
a rebuild and upload:

```bash
sam build --use-container && sam deploy --force-upload
```

---

### `sam deploy` fails with `ROLLBACK_COMPLETE`
A previous deployment attempt failed and left the CloudFormation stack in an
unrecoverable state. Delete the stuck stack before redeploying:

```bash
aws cloudformation delete-stack --stack-name music-subscription-lambda
aws cloudformation wait stack-delete-complete --stack-name music-subscription-lambda
sam build --use-container && sam deploy --guided \
  --parameter-overrides LabRoleArn=arn:aws:iam::<YOUR_ACCOUNT_ID>:role/LabRole
```

---

### CORS errors appearing in the browser console

**EC2 / ECS path:** `flask_cors` is applied globally via `CORS(app)` in `app.py`
and covers all routes automatically. If CORS errors appear, the server is likely
not running or is crashing before handling the request — check `~/flask.log` on
EC2 or `/ecs/music-subscription` in CloudWatch for ECS.

**Lambda path:** The `lambda_function.py` returns CORS headers on every
response, including OPTIONS preflight requests. If CORS errors still appear,
the request is likely hitting a route that does not exist in API Gateway, which
returns its own 403 or 404 without CORS headers. Verify that the resource and
method exist and that the API was **redeployed** after any changes.

---

### Frontend login redirects back to the login page immediately
`sessionStorage.getItem('userEmail')` in `app.js` is `null`, which means the
login API call either failed or returned a non-2xx status code. Open **Browser
DevTools → Network tab**, attempt login, and inspect the actual HTTP response
from the `/login` endpoint. The `message` field in the response body will
identify the exact cause.

---

## AWS Resources Summary

| Resource | Name / Value |
|----------|-------------|
| DynamoDB table | `login` |
| DynamoDB table | `music` |
| DynamoDB table | `subscriptions` |
| S3 bucket — artist images | `your-bucket-name` |
| S3 bucket — frontend hosting | `sonata-frontend-<your-student-id>` |
| EC2 instance | `sonata-backend` (Amazon Linux 2023, t3.micro) |
| EC2 security group | `sonata-sg` — ports 22, 5000, 8000 |
| Lambda function | `music-subscription-handler` |
| API Gateway REST API | `music-subscription-api` (deployed stage: `prod`) |
| CloudFormation stack | `music-subscription-lambda` |
| ECR repository | `music-subscription-api` |
| ECS cluster | `music-app-cluster` |
| ECS service | `music-api-service` |
| CloudWatch log group (ECS) | `/ecs/music-subscription` |
| IAM role | `LabRole` — used for EC2 instance profile, Lambda execution, and ECS task role |
| AWS region | `us-east-1` |
