# Knowledge-Codebase Backend

## Setup

1. Create a virtual environment and install dependencies:
```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and update the values:
```bash
cp .env.example .env
```

3. Run the server:
```bash
uvicorn main:app --reload
```

## S3 Media Upload Configuration

The application supports storing media files either locally or in Amazon S3.

### Local Storage (Default)
- By default, files are stored in the `media/` directory
- No additional configuration is required

### S3 Storage
To enable S3 storage:

1. Make sure you have an AWS account with S3 access
2. Create an S3 bucket for media storage
3. Update your `.env` file with the following:
```
S3_ENABLED=true
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_REGION=your-bucket-region (e.g., us-east-1)
S3_BUCKET_NAME=your-bucket-name
```

4. Make sure your bucket has appropriate CORS configuration to allow access from your application
5. Ensure your S3 bucket has public read access if you need direct public access to uploaded files

The application will automatically use S3 for media storage when `S3_ENABLED=true` and fall back to local storage if S3 upload fails. 

## Firebase Push Notifications

The application uses Firebase Cloud Messaging (FCM) to send push notifications to mobile devices.

### Setup Instructions

1. Create a Firebase project at https://console.firebase.google.com/
2. Add your iOS and Android apps to the Firebase project
3. Download and integrate the Firebase configuration files into your mobile apps
4. Get your Firebase Server Key:
   - In the Firebase Console, go to Project Settings > Cloud Messaging
   - Copy the "Server key"
5. Update your `.env` file with:
```
FIREBASE_SERVER_KEY=your_firebase_server_key_here
```

### Mobile App Integration

To receive push notifications, your mobile app needs to:

1. Initialize Firebase in your app
2. Subscribe to the topic "otd_updates" using FCM's topic subscription:
```
// iOS/Swift
Messaging.messaging().subscribe(toTopic: "otd_updates")

// Android/Kotlin
FirebaseMessaging.getInstance().subscribeToTopic("otd_updates")
```

### Testing Push Notifications

After setup, push notifications will be automatically sent when:
- A new "On This Day" entry is created

To test push notifications manually, you can use the Firebase Console's "Cloud Messaging" feature to send test messages to your devices.

alembic revision --autogenerate -m "your migration message"
alembic upgrade head