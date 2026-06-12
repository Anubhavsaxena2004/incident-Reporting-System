# AWS EC2 Deployment Report – Emergency Incident Reporting System

## Project Overview
The **Emergency Incident Reporting System** is a robust backend application powered by Django REST Framework (DRF), designed for logging, managing, assigning, and tracking incident tickets. 

Key architectural components include **PostgreSQL** for persistence, **Redis** for list and detail view caching, and **Nginx** acting as a high-performance reverse proxy. The entire stack is containerized with **Docker** and orchestrated via **Docker Compose** for secure, single-node deployments.

---

## Deployment Architecture

* **Cloud Provider**: Amazon Web Services (AWS)
* **Compute Instance**: Amazon EC2 (Ubuntu 22.04 LTS, `t3.micro`)
  * **Instance ID**: `i-03edcf60cdb47368d`
  * **Public IP Address**: `52.59.254.115`
  * **Region**: `eu-central-1` (Frankfurt)
* **Host Networking Security Group**:
  * **Port 22 (SSH)**: Allowed for remote configuration.
  * **Port 80 (HTTP)**: Exposed publicly for web client access.
  * **Port 443 (HTTPS)**: Prepared for secure TLS traffic.
* **Orchestrator**: Docker Compose (Multi-container stack)
* **Reverse Proxy**: Nginx (Direct host port binding to 80/443)
* **Database**: PostgreSQL 16 (Secure internal volume persistence)
* **Caching Layer**: Redis 7 (In-memory caching with automatic cache invalidation on save/delete hooks)

---

## Deployment Steps Performed

### 1. EC2 Instance Provisioning
Launched an EC2 instance named `incident` with Ubuntu 22.04 LTS in `eu-central-1` with public IP `52.59.254.115`.

### 2. Security Group Configuration
Assigned custom security group rules to expose SSH (22), HTTP (80), and HTTPS (443).

### 3. Connection & Docker Installation
Connected to the instance:
```bash
ssh -i first.pem ubuntu@52.59.254.115
```
Installed Docker Engine and the Docker Compose plugin, and added the `ubuntu` user to the `docker` group for rootless execution.

### 4. Git Repository Cloning & Synchronizing
Cloned the source codebase directly:
```bash
git clone https://github.com/Anubhavsaxena2004/incident-Reporting-System.git
cd incident-Reporting-System
```

### 5. Environment Configuration
Populated production secrets (`.env.prod`) containing:
* `SECRET_KEY`
* `DB_NAME`
* `DB_USER`
* `DB_PASSWORD`
* `DB_HOST`
* `ALLOWED_HOSTS` (Mapped to `52.59.254.115,localhost,web`)
* `REDIS_URL`

### 6. Production Compose Stack Initialization
Launched the multi-container stack:
```bash
docker compose -f docker-compose.prod.yml up --build -d
```
All containers started successfully:
* `incident_prod_web` (Django + Gunicorn WSGI)
* `incident_prod_db` (PostgreSQL 16)
* `incident_prod_redis` (Redis 7)
* `incident_prod_nginx` (Nginx serving static assets and proxying web connections)

### 7. Database Migrations & Static Asset Collection
The Django startup script automatically verified DB readiness, applied 100% of migrations, and collected 153 static asset files into the Nginx static volume.

### 8. Admin Credentials Creation
Provisioned the initial database administrative user:
```bash
docker exec -it incident_prod_web python manage.py createsuperuser
```

---

## Final Service Status

| Service / Container | Status | Port Binding (Internal) | Host Port Mapping |
| :--- | :--- | :--- | :--- |
| **Nginx** (`incident_prod_nginx`) | Running | 80 / 443 | `80` (HTTP) / `443` (HTTPS) |
| **Gunicorn** (`incident_prod_web`) | Running | 8000 | (Accessible via Nginx proxy only) |
| **PostgreSQL** (`incident_prod_db`) | Healthy | 5432 | (Accessible internally via Gunicorn) |
| **Redis Cache** (`incident_prod_redis`)| Running | 6379 | (Accessible internally via Gunicorn) |

---

## Deployed Application API Endpoints

### 🔐 User & Authentication APIs (`/api/users/`)
* **Registration**: `POST http://52.59.254.115/api/users/register/` (Default role: `CITIZEN`)
* **Login (Obtain JWT)**: `POST http://52.59.254.115/api/users/login/` (Returns tokens and detailed user object)
* **Refresh Token**: `POST http://52.59.254.115/api/users/token/refresh/`
* **Logout (Blacklist Token)**: `POST http://52.59.254.115/api/users/logout/`
* **User Profile**: `GET/PUT/PATCH http://52.59.254.115/api/users/me/`

### 🚨 Incident APIs (`/api/incidents/`)
* **List / Query Incidents**: `GET http://52.59.254.115/api/incidents/`
  * *Advanced Filters*: `status`, `priority`, `category`, `assigned_to`, `reported_by`.
  * *Range Query*: `created_at_gte` and `created_at_lte`.
  * *Search*: `search=leak`.
  * *Ordering*: `ordering=-priority`.
  * *Optimization*: Returns fully structured Citizen/Operator details (including IDs, usernames, and contact info) for simpler client integration.
* **File New Incident**: `POST http://52.59.254.115/api/incidents/`
* **Retrieve Incident**: `GET http://52.59.254.115/api/incidents/{incident_id}/`
* **Modify Incident**: `PUT/PATCH http://52.59.254.115/api/incidents/{incident_id}/` (Restricted by custom role-based permissions)
* **Remove Incident**: `DELETE http://52.59.254.115/api/incidents/{incident_id}/` (Restricted to Admins)
* **Incident Timeline History**: `GET http://52.59.254.115/api/incidents/{incident_id}/timeline/` (Audit trails of status changes)
* **Incident Assignment Logs**: `GET http://52.59.254.115/api/incidents/{incident_id}/assignments/`

### 🛠️ Interactive Documentation & Admin Portal
* **Swagger-UI Documentation**: [http://52.59.254.115/api/schema/swagger-ui/](http://52.59.254.115/api/schema/swagger-ui/)
* **ReDoc Reference Documentation**: [http://52.59.254.115/api/schema/redoc/](http://52.59.254.115/api/schema/redoc/)
* **Django Native Admin Panel**: [http://52.59.254.115/admin/](http://52.59.254.115/admin/)
