# Emergency Incident Reporting System – API Testing & Validation Guide

This document outlines the step-by-step workflow to test the APIs in Swagger UI or Postman. It provides the exact payloads and explains how to avoid validation errors.

---

## 🛠️ Step 1: User Registration
Create your user accounts using `POST /api/users/register/`.

### 1. Register a Citizen
* **Endpoint**: `POST http://52.59.254.115/api/users/register/`
* **JSON Request Body**:
```json
{
  "username": "citizen_alice",
  "email": "alice@example.com",
  "first_name": "Alice",
  "last_name": "Smith",
  "phone_number": "1234567890",
  "role": "CITIZEN",
  "password": "SecurePassword123!"
}
```

### 2. Register an Operator
* **Endpoint**: `POST http://52.59.254.115/api/users/register/`
* **JSON Request Body**:
```json
{
  "username": "operator_bob",
  "email": "bob@example.com",
  "first_name": "Bob",
  "last_name": "Johnson",
  "phone_number": "0987654321",
  "role": "OPERATOR",
  "password": "SecurePassword123!"
}
```

---

## 🔑 Step 2: Login (Obtain Access & Refresh Tokens)
Authenticate the user to obtain JWT tokens.

* **Endpoint**: `POST http://52.59.254.115/api/users/login/`
* **JSON Request Body**:
```json
{
  "username": "citizen_alice",
  "password": "SecurePassword123!"
}
```
* **Expected Response**:
```json
{
  "refresh": "eyJhbGci...", 
  "access": "eyJhbGci...",
  "user": {
    "id": 1,
    "username": "citizen_alice",
    "role": "CITIZEN"
  }
}
```
> [!IMPORTANT]
> To test subsequent endpoints in Swagger UI, copy the **`access`** token string, click **Authorize** at the top of the Swagger page, paste the access token, and authorize.

---

## 🚨 Step 3: Incident Management

### 1. Create a New Incident (As Citizen Alice)
* **Endpoint**: `POST http://52.59.254.115/api/incidents/`
* **Headers**: `Authorization: Bearer <access_token>`
* **JSON Request Body**:
```json
{
  "title": "Chemical Spill in Main Warehouse",
  "description": "A barrel of cleaning agent is leaking in Sector 3.",
  "category": "ACCIDENT",
  "latitude": "50.110924",
  "longitude": "8.682127",
  "address": "Building C, Industry Zone 1"
}
```
* **Note**: Do not include `"assigned_to": 0` or `"image": "string"`. Setting `"assigned_to"` to `0` or `"image"` to `"string"` will cause a validation error (`400 Bad Request`).

### 2. Retrieve All Incidents (With Filters)
* **Endpoint**: `GET http://52.59.254.115/api/incidents/?category=ACCIDENT`
* **Headers**: `Authorization: Bearer <access_token>`

---

## ⚙️ Step 4: Incident Assignment & Workflow Management

To change fields like `assigned_to`, `status`, or `priority`, you must log in as an **Admin** (using the superuser credentials created via console command `createsuperuser`) or as an **Operator** (if updating their own assigned tickets).

### 1. Assign the Ticket to Operator Bob (As Admin)
* **Endpoint**: `PATCH http://52.59.254.115/api/incidents/{incident_id}/` (replace `{incident_id}` with the UUID of the incident)
* **Headers**: `Authorization: Bearer <admin_access_token>`
* **JSON Request Body**:
```json
{
  "assigned_to": 2,
  "remarks": "Dispatching Operator Bob to contain the spill."
}
```
*(Here `2` is the ID of `operator_bob`. The ticket status will automatically transition from `REPORTED` to `ASSIGNED` due to the assignment workflow rules).*

### 2. Update Status to In-Progress (As Operator Bob)
* **Endpoint**: `PATCH http://52.59.254.115/api/incidents/{incident_id}/`
* **Headers**: `Authorization: Bearer <operator_bob_access_token>`
* **JSON Request Body**:
```json
{
  "status": "IN_PROGRESS",
  "priority": "HIGH",
  "remarks": "Arrived on site. Commencing containment."
}
```

---

## 📈 Step 5: Check Timeline and Audit Trails
These endpoints do not require request bodies (they are standard `GET` requests).

### 1. View Transition Timeline
* **Endpoint**: `GET http://52.59.254.115/api/incidents/{incident_id}/timeline/`
* **Headers**: `Authorization: Bearer <access_token>`

### 2. View Assignment History
* **Endpoint**: `GET http://52.59.254.115/api/incidents/{incident_id}/assignments/`
* **Headers**: `Authorization: Bearer <access_token>`

---

## 🔄 Step 6: Session Management

### 1. Refresh Access Token
When your access token expires after 15 minutes, you can exchange your refresh token for a new access token without logging in again.
* **Endpoint**: `POST http://52.59.254.115/api/users/token/refresh/`
* **JSON Request Body**:
```json
{
  "refresh": "<your_refresh_token_here>"
}
```

### 2. Logout (Blacklist Token)
Logs out the user and blacklists the refresh token to prevent further access.
* **Endpoint**: `POST http://52.59.254.115/api/users/logout/`
* **Headers**: `Authorization: Bearer <access_token>`
* **JSON Request Body**:
```json
{
  "refresh": "<your_refresh_token_here>"
}
```
