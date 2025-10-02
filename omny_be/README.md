# Omny Backend API

Django REST API for Omny - A Care Circle Management System with IoT Device Integration for elderly care.

## Features

- 🔐 **Firebase Authentication** - Secure user authentication with Firebase
- 👥 **Care Circle Management** - Household/care team organization
- 📱 **IoT Device Integration** - Smart watches and SOS buttons
- 🚨 **Emergency Events** - Fall detection and SOS alerts
- ⚠️ **Device Alerts** - Low battery, offline, and maintenance notifications
- 📚 **Interactive API Documentation** - Swagger UI and ReDoc

## Tech Stack

- **Django 5.2.7** - Web framework
- **Django REST Framework 3.16.1** - API framework
- **Firebase Admin SDK** - Authentication
- **drf-spectacular** - OpenAPI/Swagger documentation
- **SQLite** - Database (development)

## Prerequisites

- Python 3.10+
- Firebase project with service account credentials
- pip and virtualenv

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd omny/omny_be
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Navigate to **Project Settings** > **Service Accounts**
4. Click **"Generate New Private Key"**
5. Save the JSON file securely (e.g., `firebase-credentials.json`)

### 5. Environment Configuration

Set the Firebase credentials path as an environment variable:

```bash
export FIREBASE_CREDENTIALS_PATH="/path/to/firebase-credentials.json"
```

Or add to your shell profile (`.bashrc`, `.zshrc`, etc.):

```bash
echo 'export FIREBASE_CREDENTIALS_PATH="/path/to/firebase-credentials.json"' >> ~/.zshrc
source ~/.zshrc
```

### 6. Database Setup

Run migrations to create the database:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

Follow the prompts to create an admin account.

### 8. Run Development Server

```bash
python manage.py runserver
```

The server will start at `http://localhost:8000`

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema (JSON)**: http://localhost:8000/api/schema/

### Using the API Documentation

1. **Authentication**: Most endpoints require Firebase authentication
   - Click the **"Authorize"** button in Swagger UI
   - Enter your Firebase ID token in the format: `Bearer <your_token>`
   - Click **"Authorize"** to save

2. **Testing Endpoints**: 
   - Expand any endpoint
   - Click **"Try it out"**
   - Fill in the required parameters
   - Click **"Execute"**

## API Endpoints Overview

### Authentication (`/api/auth/`)

- `POST /api/auth/register/` - Register a new user
- `POST /api/auth/login/` - Login user
- `POST /api/auth/verify/` - Verify Firebase token
- `GET /api/auth/profile/` - Get user profile
- `PATCH /api/auth/profile/` - Update user profile
- `POST /api/auth/logout/` - Logout user

### Devices (`/api/devices/`)

- `POST /api/devices/register/` - Register a new device
- `GET /api/devices/` - List all household devices
- `GET /api/devices/<device_id>/` - Get device details
- `PATCH /api/devices/<device_id>/` - Update device
- `DELETE /api/devices/<device_id>/` - Delete device

### Alerts (`/api/devices/alerts/`)

- `POST /api/devices/alerts/create/` - Create device alert
- `GET /api/devices/alerts/` - List device alerts
- `POST /api/devices/alerts/<alert_id>/acknowledge/` - Acknowledge alert

### Emergencies (`/api/devices/emergencies/`)

- `POST /api/devices/emergencies/create/` - Create emergency event
- `GET /api/devices/emergencies/` - List emergency events
- `POST /api/devices/emergencies/<emergency_id>/respond/` - Respond to emergency

## Project Structure

```
omny_be/
├── authentication/          # User authentication app
│   ├── models.py           # User and Household models
│   ├── views.py            # Authentication views
│   ├── middleware.py       # Firebase authentication
│   └── schema.py           # OpenAPI schema extension
├── devices/                # IoT devices app
│   ├── models.py           # Device, Alert, Emergency models
│   ├── views.py            # Device management views
│   └── serializers.py      # DRF serializers
├── omny_be/                # Project settings
│   ├── settings.py         # Django settings
│   └── urls.py             # URL configuration
├── manage.py               # Django management script
└── requirements.txt        # Python dependencies
```

## Database Models

### User & Household
- **User** - Custom user model with Firebase UID
- **Household** - Care circle/household grouping

### Devices
- **Space** - Physical rooms/locations
- **Device** - IoT devices (watches, SOS buttons)
- **DeviceAlert** - Non-emergency alerts
- **EmergencyEvent** - Emergency events (falls, SOS)
- **SOSButtonConfiguration** - SOS button tap patterns

## Development

### Running Migrations

After model changes:

```bash
python manage.py makemigrations
python manage.py migrate
```

### Creating a New App

```bash
python manage.py startapp <app_name>
```

Don't forget to add it to `INSTALLED_APPS` in `settings.py`.

### Django Admin

Access the admin interface at http://localhost:8000/admin/

Use the superuser credentials created earlier.

## Common Tasks

### Reset Database

```bash
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

### View All URLs

```bash
python manage.py show_urls  # Requires django-extensions
# Or manually check urls.py files
```

### Run Tests

```bash
python manage.py test
```


## API Authentication Flow

### Client-Side (Frontend)

1. User signs in with Firebase Authentication
2. Get Firebase ID token: `await user.getIdToken()`
3. Include token in API requests:
   ```javascript
   headers: {
     'Authorization': `Bearer ${idToken}`,
     'Content-Type': 'application/json'
   }
   ```

### Server-Side (Backend)

1. Extract token from `Authorization` header
2. Verify token with Firebase Admin SDK
3. Retrieve user from database using `firebase_uid`
4. Attach user to request object

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests
4. Submit a pull request

---

**Built with ❤️ for better elderly care**
