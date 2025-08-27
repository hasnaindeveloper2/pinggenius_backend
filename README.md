# PingGenius Backend FastAPI

A backend service for PingGenius built with FastAPI.

## Features

- RESTful API endpoints
- Fast performance with FastAPI
- Database integration
- Authentication and authorization
- API documentation with Swagger/OpenAPI

## Getting Started

### Prerequisites

- Python 3.8+
- pip
- virtualenv (recommended)

### Installation

1. Clone the repository
```bash
git clone []
```

2. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

### Running the Server

```bash
uvicorn main:app --reload
```

## API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.