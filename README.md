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