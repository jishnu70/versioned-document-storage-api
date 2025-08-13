# Versioned Document Storage API

## Overview
The Versioned Document Storage API is a FastAPI-based web application designed to provide secure user authentication and file storage with version control. It allows users to register, log in, upload files, and manage multiple versions of their files. The system uses asynchronous database operations with SQLAlchemy, Redis for OTP storage, and Celery for asynchronous email tasks.

## Features
- **User Authentication**: Register and log in with OTP-based email verification.
- **File Storage**: Upload files with automatic versioning.
- **Version Control**: Retrieve specific file versions or all versions of a file.
- **Secure Token Management**: JWT-based access and refresh tokens for secure API access.
- **Asynchronous Processing**: Uses Celery for sending OTP emails and SQLAlchemy for async database operations.
- **File Integrity**: SHA-256 checksums to prevent duplicate file uploads.

## Tech Stack
- **Framework**: FastAPI
- **Database**: SQLite/PostgreSQL (configurable via `DATABASE_URL`)
- **ORM**: SQLAlchemy with async support
- **Task Queue**: Celery with Redis backend
- **Cache**: Redis for OTP storage
- **Authentication**: JWT (JSON Web Tokens)
- **Email**: SMTP for sending OTP emails (configured for Gmail)
- **File Storage**: Local filesystem with structured storage
- **Dependencies**: Managed via `uv` (as seen in `uv.lock`)

## Prerequisites
- Python 3.8+
- Redis server running on `localhost:6379`
- SMTP server credentials (e.g., Gmail SMTP)
- SQLite or PostgreSQL database
- `uv` or `pip` for dependency management

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/jishnu70/versioned-document-storage-api.git
   cd versioned-document-storage-api
   ```

2. **Set Up a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   Using `uv`:
   ```bash
   uv sync
   ```
   Or with `pip`:
   ```bash
   pip install -r req.txt
   ```

4. **Configure Environment Variables**:
   Create a `.env` file in the project root with the following:
   ```env
   DATABASE_URL=sqlite+aiosqlite:///data.db
   SECRET_KEY=your_jwt_secret_key
   JWT_ALGORITHM=HS256
   MAIL_ACCOUNT=your_email@gmail.com
   MAIL_PASSWORD=your_app_specific_password
   ```
   - Replace `your_jwt_secret_key` with a secure random string.
   - For Gmail, use an App Password if 2FA is enabled.

5. **Start Redis Server**:
   Ensure Redis is running on `localhost:6379`. For example:
   ```bash
   redis-server
   ```

6. **Run Celery Worker**:
   In a separate terminal, start the Celery worker:
   ```bash
   celery -A app.background.celery_app.celery_app worker --loglevel=info
   ```

7. **Run the Application**:
   ```bash
   uvicorn app.main:app --host localhost --port 8000 --reload
   ```

8. **Access the API**:
   - Open `http://localhost:8000/docs` for the interactive Swagger UI.
   - The root endpoint (`/`) returns `{"message": "backend is online"}`.

## Project Structure
```
versioned-document-storage-api/
├── app/
│   ├── __init__.py
│   ├── authentication/
│   │   ├── services.py        # User registration and OTP verification logic
│   │   ├── tokenManager.py    # JWT token creation and validation
│   ├── background/
│   │   ├── celery_app.py      # Celery configuration for async tasks
│   │   ├── OtpService.py      # OTP generation and email sending
│   ├── dependencies/
│   │   ├── User.py            # Dependency for fetching authenticated user
│   ├── infrastructure/
│   │   ├── file_storage.py    # Local file storage operations
│   │   ├── redis_client.py    # Redis client configuration
│   ├── models/
│   │   ├── File.py            # SQLAlchemy model for files
│   │   ├── FileVersion.py     # SQLAlchemy model for file versions
│   │   ├── User.py            # SQLAlchemy model for users
│   ├── routes/
│   │   ├── authRoutes.py      # Authentication endpoints (login, register, verify)
│   │   ├── fileRoutes.py      # File management endpoints
│   ├── schemas/
│   │   ├── FileSchemas.py     # Pydantic schemas for file responses
│   │   ├── Otp.py             # Pydantic schemas for OTP requests/responses
│   │   ├── Token.py           # Pydantic schemas for token responses
│   │   ├── User.py            # Pydantic schemas for user data
│   ├── service/
│   │   ├── File_service.py    # Business logic for file operations
│   ├── utils/
│   │   ├── hash_util.py       # Utility for hashing file contents
│   ├── config.py              # Application configuration with Pydantic
│   ├── database.py            # Database setup with SQLAlchemy
│   ├── main.py                # FastAPI app initialization
├── uploads/                   # Directory for stored files
├── data.db                   # SQLite database file
├── dump.rdb                  # Redis dump file
├── req.txt                   # Dependency list
├── uv.lock                   # Dependency lock file
├── README.md                 # This file
```

## 📚 API Documentation

- **📊 Swagger UI**: http://localhost:8000/docs
- **📖 ReDoc**: http://localhost:8000/redoc

## 🔌 API Endpoints

### 🔐 Authentication Routes

| Route | Method | Auth Required | Description | Response |
|-------|--------|---------------|-------------|----------|
| `/auth/register` | `POST` | ❌ | Register new user account | Returns task ID and user ID |
| `/auth/register-verify` | `POST` | ❌ | Verify account with email OTP | Confirms account activation |
| `/auth/login` | `POST` | ❌ | User login (sends OTP to email) | Returns task ID for OTP process |
| `/auth/verify` | `POST` | ❌ | Verify login OTP and receive JWT tokens | Returns access & refresh tokens |

### 📁 File Management Routes

| Route | Method | Auth Required | Description | Response |
|-------|--------|---------------|-------------|----------|
| `/file/` | `GET` | ✅ | List all files for authenticated user | Array of user's files with versions |
| `/file/{file_name}` | `GET` | ✅ | Get file information and versions | File metadata and version list |
| `/file/{file_name}?all=true` | `GET` | ✅ | Get all versions of specific file | Complete version history |
| `/file/{file_name}/{version_id}` | `GET` | ✅ | Download specific file version | File download stream |
| `/file/` | `POST` | ✅ | Upload new file or create new version | Success message with version ID |

## 💻 Usage Examples

### User Registration
```bash
# Register user
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "securepassword",
    "confirm_password": "securepassword"
  }'

# Verify with OTP from email
curl -X POST "http://localhost:8000/auth/register-verify" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "otp": "123456"
  }'
```

### Authentication
```bash
# Login
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "password": "securepassword"
  }'

# Verify login OTP
curl -X POST "http://localhost:8000/auth/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "otp": "654321"
  }'
```

### File Operations
```bash
# Upload file
curl -X POST "http://localhost:8000/file/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@document.pdf"

# List files
curl -X GET "http://localhost:8000/file/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Download file
curl -X GET "http://localhost:8000/file/document.pdf/VERSION_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  --output document.pdf
```

## ⚙️ Configuration

### Environment Variables
- `DATABASE_URL`: Database connection string
- `SECRET_KEY`: JWT signing secret
- `JWT_ALGORITHM`: JWT algorithm (default: HS256)
- `MAIL_ACCOUNT`: SMTP email address
- `MAIL_PASSWORD`: SMTP password (use app passwords for Gmail)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/name`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push to branch (`git push origin feature/name`)
5. Create Pull Request
