# 🚆 RailSathi Backend

<div align="center">

![RailSathi Logo](https://img.shields.io/badge/🚆-RailSathi-007aff?style=for-the-badge)

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)

*A modern microservice for railway complaint management with intelligent deployment features*

</div>

## ✨ Features

- 🔄 **Smart Environment Detection** - Automatically detects Docker vs Docker Compose environments
- 🔌 **Dynamic Host Configuration** - Intelligently connects to the appropriate database host
- 🚀 **Zero-Config Deployment** - Just run and go with automatic database initialization
- ⏱️ **wait-for-it.sh** - Handles database startup timing to prevent connection issues
- 📤 **File Upload Support** - Handle complaint attachments and media effortlessly
- 📊 **Swagger Documentation** - Beautiful API docs built-in
- 🔄 **Hot Reloading** - Code changes reflect instantly in development
- 🛡️ **Production Ready** - Built with security and performance in mind

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) (included in Docker Desktop)
- [Git](https://git-scm.com/downloads) (for cloning the repository)

### One-Minute Setup

```bash
# Clone repository
git clone https://github.com/s2pl/RailSathiBE.git
cd RailSathiBE

# Start with Docker Compose (API + Database)
docker-compose up -d

# Or build and run just the API container
docker build -t my-fastapi-app .
docker run --env-file .env -d --name fastapi-container -p 8000:8000 my-fastapi-app
```

🌟 **Access the application at [http://localhost:8000/items](http://localhost:8000/items)**

## 🧙‍♂️ Smart Environment Features

RailSathi automatically detects its environment and configures database connections intelligently:

- **Docker Compose**: Uses `postgres` as the hostname
- **Standalone Docker**: Uses `host.docker.internal` to connect to your host machine's database

## 🛠️ Detailed Setup Guide

### 1️⃣ Environment Configuration

The `.env` file contains all the configuration options:

```env
# PostgreSQL Configuration
POSTGRES_HOST=postgres            # Default host (auto-detected at runtime)
POSTGRES_HOST_DOCKER=host.docker.internal  # Host for standalone Docker
POSTGRES_HOST_COMPOSE=postgres    # Host for Docker Compose
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=1234
POSTGRES_DB=railsathibe

# FastAPI Settings
API_PORT=8000

# Email Configuration (Optional)
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
MAIL_FROM=your-email@example.com

# Cloudinary Configuration for File Storage
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

### ☁️ Setting Up Cloudinary

The application uses Cloudinary for storing complaint media files. To set up your own Cloudinary account:

1. Create a free account at [Cloudinary](https://cloudinary.com/users/register/free)
2. Navigate to your Cloudinary dashboard
3. Copy your Cloud Name, API Key, and API Secret
4. Add these values to your `.env` file

### 2️⃣ Running with Docker Compose (recommended)

Run both the FastAPI application and PostgreSQL database:

```bash
# Build and run docker compose
docker-compose build --no-cache


# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Reset everything (including database volume)
docker-compose down -v
```

### 3️⃣ Running with Docker (standalone)

If you already have PostgreSQL running on your machine:

```bash
# Build the image
docker build -t my-fastapi-app .

# Run the container
docker run --env-file .env -d --name fastapi-container -p 8000:8000 my-fastapi-app

# View logs
docker logs -f fastapi-container

# Stop container
docker stop fastapi-container
docker rm fastapi-container
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/items` | Health check & homepage |
| GET    | `/items/complaint/{id}` | Get complaint by ID |
| GET    | `/items/complaints/{date}` | Get complaints by date |
| POST   | `/items/complaint` | Create a new complaint |
| PUT    | `/items/complaint/{id}` | Update a complaint |
| DELETE | `/items/complaint/{id}` | Delete a complaint |
| DELETE | `/items/complaint/{id}/media` | Delete complaint media |

📚 **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

## 🧠 Architecture

```
RailSathi Backend
├── 🐳 Docker Layer
│   ├── FastAPI Container
│   │   ├── Application Code
│   │   ├── SQL Initialization Scripts
│   │   └── Dynamic Host Detection
│   └── PostgreSQL Container
│       └── Persistent Volume
├── 🔄 Database Layer
│   ├── Tables & Schemas
│   └── Indexes
└── 🌐 API Layer
    ├── Endpoints
    ├── Validation
    └── Business Logic
```

## 🔧 Development

### Database Migrations

SQL initialization scripts are automatically run when the PostgreSQL container is created:

- `01-init-db.sql` - Creates the database schema
- `02-add_test_users.sql` - Seeds test data

### Modifying Database Schema

To update the database schema:

1. Modify the SQL scripts in the project directory
2. Rebuild and restart the containers

```bash
docker-compose down -v  # Remove volumes to ensure fresh DB initialization
docker-compose up -d --build
```

## 🔍 Troubleshooting

### Common Issues

- **Database Connection Errors**: Check if PostgreSQL is running and accessible
- **Port Conflicts**: Ensure ports 8000 and 5432 are available
- **Volume Permission Issues**: May occur on Linux systems, try running Docker with sudo

### Useful Commands

```bash
# Check container status
docker ps -a

# View container logs
docker logs fastapi-container

# Connect to PostgreSQL inside container
docker exec -it railsathi-postgres psql -U postgres -d railsathibe

# Execute SQL file manually
docker exec -i railsathi-postgres psql -U postgres -d railsathibe < 01-init-db.sql
```

## 📈 Future Enhancements

- [ ] CI/CD pipeline integration
- [ ] Kubernetes deployment manifests
- [ ] Enhanced monitoring and logging
- [ ] Performance optimization

## 👁‍🗨 Design Decisions & Assumptions

### Architectural Decisions

- **SQL Scripts over ORM**: Direct SQL scripts for database initialization instead of an ORM to keep dependencies minimal.
- **Smart Environment Detection**: Runtime detection of environment to support both standalone Docker and Docker Compose without configuration changes.
- **File Storage**: Cloudinary for media files rather than local storage for better scaling and CDN benefits.
- **Authentication**: Simple API key authentication used for this microservice scope.

### Important Notes

- **The Provided Assignment Repo is Built with FastAPI, NOT Django**: This project is implemented using FastAPI framework, not Django. Therefore, you CANNOT create a superuser using Django's `python manage.py createsuperuser` command as it does not exist in this project.
- **No Django Admin Interface**: Since this is not a Django application, there is no Django admin interface available.
- **No Superuser Creation Command**: User management is handled through SQL scripts (see `02-add_test_users.sql`) or API endpoints.
- **Raw SQL**: Database schema is defined in raw SQL files, not through Django models or migrations.
- **Test Data**: The application comes with test data for quick evaluation and testing.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**🚆 RailSathi** | Built with ❤️ by the Deep Saha

</div>