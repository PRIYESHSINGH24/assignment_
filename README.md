# Step 1: Environment Setup & Django Project

First, verify your system has python installed.
```bash
python3 --version
```
This project has been configured to with python 3.14 to ensure that is supports all the latest feature.

Now, check if <b>uv</b> is installed:
```bash
uv --version
```

If uv is not installed, install it:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Initialize the Python environment with uv:
```bash
uv init --python 3.14
```
This commands creates a pyproject.toml file.
Now, lets add the required dependencies:
```bash
uv add Django djangorestframework djangorestframework-simplejwt psycopg python-decouple django-filter drf-spectacular
```

Add the developement dependencies for testing as well.

```bash
uv add --dev pytest pytest-django pytest-cov
```

Create a virtual environment and activate it:
```bash
uv venv
source .venv/bin/activate
uv sync
```

Now create the Django project:
```bash
django-admin startproject config .
```

### Verification

Run Django`s built in checks:
```bash
python manage.py check
```

# Step 2: PostgreSQL & Enviornment Configuration
Set up a local PostgreSQL database, configure Django to use it via environment variables, and verify the connection.

First, verify PostgreSQL is installed:
```bash
psql --version
```

If PostgreSQL is not installed, install it or set the DATABASE_URL

Now, create .env file in the root project.
```bash
touch .env
```

Now, set the values in it. Check .env.example for to list the values to set in .env

```bash
Ensure that all the changes are migrated to database.
```

# Understanding the Architecture

This project contains multiple apps. Each app handles a specific feature domain:

| App         |                      Responsibility                       |
|:------------|:---------------------------------------------------------:|
| users       |           User model, signup, login, JWT tokens           |
| diagnostics |   Diagnositcs Centres, Tests, centre-test relationships   |
| bookings    |    Booking Model, Booking Creation, Status Transition     |
| payments    |    Payment model, Payment Processing, payment webhook     |
| common      | Shared utilities: pagination, permissions, error response |

This project uses JWT authentication.
Access Token is valid for 1 hour.
Refresh token is valid for 7 hour.

## API Documentation

This project uses Django REST Framework and drf-spectacular to generate OpenAPI documentation.
Available Documentation Endpoints

| Endpoint | 	Description | 
|:------------|:---------------------------------------------------------:|
| /api/schema/	| Returns the OpenAPI schema in JSON format. | 
| /api/docs/ | 	Interactive API documentation using Swagger UI. | 
| /api/redoc/	| API documentation using ReDoc. | 

# Testing Configuration

This is configured with pytest and pytest-django. So, we can write and run tests throughout the project.
To measure code coverage in a Python project using pytest, we have pytest-cov.


# API Endpoints


API Endpoints
### Authentication
- POST /api/v1/auth/signup/ - User registration
- POST /api/v1/auth/login/ - User login
- POST /api/v1/auth/token/refresh/ - Refresh access token
- GET /api/v1/auth/profile/ - Get authenticated user profile
### Diagnostic Centres
- GET /api/v1/diagnostics/centres/ - List all diagnostic centres (paginated)
- GET /api/v1/diagnostics/centres/{id}/ - Get centre details with tests
- POST /api/v1/diagnostics/centres/ - Create centre (staff only)
- PUT /api/v1/diagnostics/centres/{id}/ - Update centre (staff only)
- DELETE /api/v1/diagnostics/centres/{id}/ - Delete centre (staff only)
- GET /api/v1/diagnostics/centres/{id}/tests/ - List tests at a centre
### Diagnostic Tests
- GET /api/v1/diagnostics/tests/ - List all diagnostic tests
- GET /api/v1/diagnostics/tests/{id}/ - Get test details
- POST /api/v1/diagnostics/tests/ - Create test (staff only)
- PUT /api/v1/diagnostics/tests/{id}/ - Update test (staff only)
- DELETE /api/v1/diagnostics/tests/{id}/ - Delete test (staff only)
### Centre-Test Relationships
- GET /api/v1/diagnostics/centre-tests/ - List centre-test relationships
- POST /api/v1/diagnostics/centre-tests/ - Create relationship (staff only)
### Bookings
- GET /api/v1/bookings/ - List user's bookings (paginated)
- GET /api/v1/bookings/{id}/ - Get booking details
- POST /api/v1/bookings/ - Create a new booking
- POST /api/v1/bookings/{id}/cancel/ - Cancel a booking
### Payments
- POST /api/v1/payments/ - Create payment for a booking
- POST /api/v1/payments/process/ - Process payment (success/failure)
- POST /api/v1/payments/webhook/ - Receive payment webhook (idempotent)
