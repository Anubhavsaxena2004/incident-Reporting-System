# Emergency Incident Reporting System - Backend

Production-ready Django 5 / DRF Emergency Incident Reporting System, containerized with Docker and structured for clean deployment with Gunicorn and Nginx.

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- **Python 3.12**
- **PostgreSQL 16/17** (or run via Docker)

### 2. Environment Configuration
Create a `.env` file in the root directory (based on `.env.example`):
```env
# Django Settings
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,web

# PostgreSQL Settings
DB_NAME=incident_db
DB_USER=postgres
DB_PASSWORD=your-local-postgres-password
DB_HOST=localhost
DB_PORT=5432
```

### 3. Setup Virtual Environment & Database
Inside the database terminal (or pgAdmin Query tool), create the database:
```sql
CREATE DATABASE incident_db;
```

Run the setup commands:
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/local.txt

# Run migrations
python manage.py migrate

# Load / Run system check
python manage.py check

# Start development server
python manage.py runserver
```

---

## 🐳 Docker Deployment

### 1. Local Development Stack (Django Server + PostgreSQL Container)
Starts PostgreSQL inside a container while mapping database parameters.
```bash
# Build and start services in background
docker compose up --build -d

# Run migrations inside django container
docker compose exec web python manage.py migrate

# Stop services
docker compose down
```

### 2. Production Stack (Gunicorn + Nginx + Postgres + Redis + Volumes)
Orchestrates a secure Gunicorn WSGI server proxied behind Nginx (directly exposing ports `80` and `443`), utilizing Postgres for database storage and Redis for views caching.

#### AWS EC2 Single-Instance Deployment Instructions

##### Step 1: Provision the AWS EC2 Instance
- Launch a new EC2 Instance (Ubuntu 22.04 LTS is recommended, `t3.micro` or `t3.medium`).
- **Security Group Settings**: Add inbound rules to allow:
  - **SSH** (Port 22) - restricted to your IP.
  - **HTTP** (Port 80) - Anywhere (`0.0.0.0/0`, `::/0`).
  - **HTTPS** (Port 443) - Anywhere (`0.0.0.0/0`, `::/0`).

##### Step 2: Install Docker and Docker Compose on EC2
SSH into your instance and install Docker:
```bash
# SSH connect to your host
ssh -i your-key.pem ubuntu@your-ec2-public-ip

# Update packages and install Docker
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2

# Start and enable Docker
sudo systemctl enable docker
sudo systemctl start docker

# Add your user to the docker group (avoids typing sudo for docker commands)
sudo usermod -aG docker $USER

# Log out and log back in to apply the group membership changes
exit
```

##### Step 3: Clone Code and Populate Production Environment
```bash
# Reconnect to the instance
ssh -i your-key.pem ubuntu@your-ec2-public-ip

# Clone the repository
git clone https://github.com/Anubhavsaxena2004/incident-Reporting-System.git
cd incident-Reporting-System

# Create production environment file from the template
cp .env.prod.example .env.prod

# Edit .env.prod to populate secrets
nano .env.prod
```
*Note: Make sure to set `DEBUG=False` and include your EC2 public IP or domain name under `ALLOWED_HOSTS`.*

##### Step 4: Boot the Stack
Build and launch all containers in background mode:
```bash
# Build and run containers
docker compose -f docker-compose.prod.yml up --build -d

# Check status of running containers
docker compose -f docker-compose.prod.yml ps

# Inspect logs to verify successful boot
docker compose -f docker-compose.prod.yml logs -f web
```
*(The startup entrypoint automatically runs database migrations and collects static files).*

##### Step 5: Create Admin Superuser
```bash
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```


---

## 🛡️ Environment Variables
The application consumes variables loaded from `.env` (development) or `.env.prod` (production):
- `SECRET_KEY`: Cryptographic signing key for sessions and JWT.
- `DEBUG`: Controls verbose exception traces (`True` in dev, `False` in prod).
- `ALLOWED_HOSTS`: Permitted host headers.
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`: Database connection details.
- `CORS_ALLOWED_ORIGINS`: Allowed cross-origin API hosts.
- `SECURE_SSL_REDIRECT`: Forces all HTTP requests to redirect to HTTPS.

---

## 📋 API Endpoints Reference

### 🔐 User & Authentication (`/api/users/`)
All authentication operations use JSON Web Tokens (SimpleJWT).

| Endpoint | Method | Description | Auth Required | Payload / Query |
| :--- | :--- | :--- | :--- | :--- |
| `/api/users/register/` | POST | Register a new user (role: `CITIZEN` by default) | No | `{"username", "password", "email", "first_name", "last_name", "phone_number", "role"}` |
| `/api/users/login/` | POST | Login and obtain access + refresh tokens | No | `{"username", "password"}` |
| `/api/users/token/refresh/` | POST | Renew access token | No | `{"refresh"}` |
| `/api/users/logout/` | POST | Terminate session (blacklist refresh token) | Yes (Bearer) | `{"refresh"}` |
| `/api/users/me/` | GET/PUT/PATCH | Retrieve / update caller profile details | Yes (Bearer) | (Profile details json) |

---

### 🚨 Incident Management (`/api/incidents/`)

| Endpoint | Method | Description | Auth Required | Roles Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `/api/incidents/` | GET | List incidents | Yes (Bearer) | **Citizens**: view own only.<br>**Operators / Admins**: view all. Supports sorting, searching, and advanced filtering. |
| `/api/incidents/` | POST | File a new incident | Yes (Bearer) | Automatically binds caller as reporter. Checks coordinates and XSS text inputs. |
| `/api/incidents/<id>/` | GET | View incident details | Yes (Bearer) | Access checked via object-level permissions. |
| `/api/incidents/<id>/` | PUT/PATCH | Update incident | Yes (Bearer) | **Citizens**: details only while `REPORTED`. No workflow changes.<br>**Operators / Admins**: status and priority. |
| `/api/incidents/<id>/` | DELETE | Hard delete record | Yes (Bearer) | Strictly restricted to **Admins**. |
| `/api/incidents/<id>/timeline/` | GET | Status transition logs | Yes (Bearer) | Audit trail of status histories and remarks. |
| `/api/incidents/<id>/assignments/` | GET | Delegation logs | Yes (Bearer) | Audit trail of assignee updates. |

---

## 🔍 Filtering, Searching, & Sorting Query Parameters
The `/api/incidents/` endpoint supports advanced URL queries:
- **Filtering**: `status`, `priority`, `category`, `assigned_to`, `reported_by`.
- **Date Ranges**: `created_at_gte` and `created_at_lte` (e.g. `/api/incidents/?created_at_gte=2026-06-11T00:00:00Z`).
- **Full-Text Search**: `/api/incidents/?search=chemical leak` (searches `title`, `description`, `address`).
- **Ordering**: `/api/incidents/?ordering=priority` (prefix with `-` for descending).

---

## 🛠️ Interactive Documentation (OpenAPI / Swagger UI)
Interactive sandboxes compile automatically from Django model structures and are routed at:
- **Swagger UI**: [http://localhost:8000/api/schema/swagger-ui/](http://localhost:8000/api/schema/swagger-ui/)
- **ReDoc reference**: [http://localhost:8000/api/schema/redoc/](http://localhost:8000/api/schema/redoc/)
- **Raw Schema Description**: [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/)

---

## 🧪 Running Tests & System Verifications
A complete integration test suite containing `24` test cases covers all components.
```bash
# Run tests inside local virtual environment (uses SQLite automatically)
python manage.py test

# Verify Django project system check compiles cleanly
python manage.py check
```
