## 📝 Notes API

A high-performance **FastAPI** application designed for managing notes, incorporating advanced features like **Redis caching**, **rate limiting**, **soft delete**, and tracking **recently viewed notes**. This project serves as a technical assessment submission for a Junior Python Backend Developer role.

-----

### ✨ Features Implemented

The API is built to meet core requirements while including several production-ready and creative features.

#### Core Requirements ✓

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/notes` | **POST** | Create a new note (with validation for `title`, `content`, `tags`, `is_public`, `is_pinned`). |
| `/notes/{note_id}` | **GET** | Retrieve a single note. Implements **Redis caching** and tracks **recently viewed notes**. |
| `/notes` | **GET** | List notes with optional filtering (`is_public`, `is_pinned`, `tags`, `offset`, `limit`). Can include soft-deleted notes. |
| `/notes/{note_id}` | **DELETE** | **Permanently** delete a note from the database. |
| `/notes/softdelete/{note_id}` | **DELETE** | **Soft delete** a note by setting the `deleted_at` timestamp. |
| `/notes/restore/{note_id}` | **POST** | Restore a soft-deleted note. |
| `/notes/recent` | **GET** | Retrieve up to 10 **recently viewed notes** for a given `user_id`, ordered by most recent first. |

-----

#### 🛡️ Rate Limiting Strategy

  * **Limit:** 100 requests per 10 minutes per client IP.
  * **Implementation:** Used `fastapi-limiter` with **Redis** using a sliding window strategy.
  * **Response:** Returns **HTTP 429 Too Many Requests** if the limit is exceeded.

-----

#### 💡 Creative & Production-Ready Features

  * **Soft Delete:** Notes are excluded from standard queries unless `show_deleted=True` is specified. Allows for note recovery.
  * **Recently Viewed Notes:** Tracks a user's last 10 viewed notes in Redis for quick access.
  * **Redis Caching:** Single notes are cached for **1800 seconds (30 minutes)**. Cache is invalidated on update, soft delete, or hard delete.
  * **Structured Logging:** Uses a **Rotating File Handler** to capture INFO, WARNING, and ERROR logs, preventing log files from growing indefinitely.
  * **Containerization:** Full support via `Dockerfile` and `docker-compose.yml`.

-----

### 🏛️ Design Decisions

| Feature | Decision | Rationale |
| :--- | :--- | :--- |
| **Rate Limiting** | Redis Sliding Window | Simplicity, reliability, and accuracy across distributed environments. |
| **Caching Strategy** | 30-minute TTL for individual notes | Reduces database load for frequently accessed notes while keeping data reasonably fresh. |
| **Database** | PostgreSQL with `asyncpg` | Excellent support for high concurrency and native async operations, well-suited for FastAPI. |
| **Persistence** | Redis vs In-Memory | **Redis** was chosen for **durability**, built-in **concurrency**, and native rate-limiting support. |
| **Soft Delete** | `deleted_at` Timestamp | Allows for **data recovery** and auditing, despite slightly more complex query logic. |

-----

### 📦 Project Structure

```
project/
│   alembic/
│       └── env.py              # Alembic environment for migrations
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application and Rate Limiter setup
│   ├── config/database.py      # DB connection (PostgreSQL) and Redis connection setup
│   ├── models.py               # SQLAlchemy ORM models (Database Schemas)
│   ├── schema.py               # Pydantic models (Data validation)
│   ├── service.py              # Core business logic for notes, caching, and recent notes
│   ├── middleware.py           # Logging middleware class
│   └── routers/
│       └── notes.py            # API endpoints for notes
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

-----

### ⚙️ Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/notesdb
REDIS_URL=redis://localhost:6379/0
```

-----

### 🚀 Installation & Running Locally

#### Using Python/Uvicorn

1.  **Clone the repository:**
    ```bash
    git clone <repo-url>
    cd project
    ```
2.  **Setup and activate virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run database migrations with Alembic:**
    ```bash
    alembic upgrade head
    ```
5.  **Run the application:**
    ```bash
    uvicorn app.main:app --reload
    ```

#### Using Docker (Recommended for Production Setup)

The `docker-compose.yml` file includes services for the FastAPI app, PostgreSQL, and Redis, along with initial migration support.

```bash
docker-compose up --build 
```

Once running, view the Swagger documentation: **`http://localhost:8000/docs`**

-----

### 🖥️ API Usage Examples

#### **Create a Note**

**POST** `/api/v1/notes`

```json
{
  "title": "Welcome",
  "content": "This is a sample note.",
  "tag": ["welcome", "intro"],
  "is_public": true,
  "is_pinned": false
}
```

#### **Get Recently Viewed Notes**

**GET** `/api/v1/notes/recent?user_id=an12`

#### **Soft Delete a Note**

**DELETE** `/api/v1/notes/softdelete/1`

#### **Hard Delete a Note (Permanent)**

**DELETE** `/api/v1/notes/1`

#### **Restore a Soft-Deleted Note**

**POST** `/api/v1/notes/restore/1`

-----

### 📝 Logging

All requests and database operations are captured using a **RotatingFileHandler**.

  * Logs automatically **rotate** when they reach a certain size, which is critical for long-running services.
  * Logs include key information such as the **HTTP method**, affected **note IDs**, and full **error details**.

### 🔮 Future Features

1. JWT for Authentication and Authorization
    Feature: Implementation of JSON Web Tokens (JWT) for secure user authentication and authorization.
    Reasoning:
        Security: Moves the application beyond simple user ID passing, ensuring that only authenticated and authorized users can access or modify their notes.

2. Comprehensive Testing with Pytest
    Feature: Introduction of a thorough test suite using the Pytest framework, covering unit, integration, and API endpoint tests.
    Reasoning:
    ensure that core functionalities (CRUD operations, caching, soft delete, rate limiting) work as expected and prevent regressions when new features are added or dependencies are updated.