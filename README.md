# GPT Email Forwarder

An intelligent email forwarding system that uses OpenAI's GPT to automatically process, categorize, and forward emails. Extracts project details from emails and integrates with Google Sheets and Google Drive.

## Features

- Automatic email processing and forwarding using GPT-3.5-turbo
- Project matching and item extraction
- Google Sheets integration for project items
- Google Drive storage for emails and attachments
- FastAPI web service for configuration management

## Prerequisites

- Python 3.10+
- PostgreSQL database
- Google Cloud Service Account (Drive & Sheets API enabled)
- OpenAI API key
- Email account with IMAP/SMTP access

## Installation

### Docker Compose

1. Set environment variables:
   ```bash
   export DATABASE_URL="postgresql+psycopg2://postgres:postgres@postgres_db:5432/postgres"
   export GOOGLE_SERVICE_ACCOUNT_KEY_JSON='{"type":"service_account",...}'
   ```

2. Create Docker network and volume:
   ```bash
   docker network create email-forwarder
   docker volume create pgdata
   ```

3. Start services:
   ```bash
   docker-compose up -d
   ```

### Manual Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/dbname"
   export GOOGLE_SERVICE_ACCOUNT_KEY_JSON='{"type":"service_account",...}'
   ```

3. Run services:
   ```bash
   # Web API
   uvicorn main:app --host 0.0.0.0 --port 8000
   
   # Email forwarder
   python email_forwarder.py
   ```

## Configuration

Configuration is managed via the FastAPI web service at `http://localhost:8000/`.

**Get configuration:**
```bash
curl http://localhost:8000/
```

**Update configuration:**
```bash
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d @config.json
```

Configuration JSON structure:
```json
{
  "imap_host": "imap.gmail.com",
  "imap_port": 993,
  "email": "your-email@example.com",
  "password": "your-app-password",
  "openai_api_key": "sk-...",
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 465,
  "prompt_subject_line": "...",
  "prompt_forward_email": "...",
  "prompt_project": "...",
  "receiver_emails": [
    {"name": "order", "email": "orders@example.com", "header": "<p>...</p>"}
  ],
  "projects": [
    {
      "name": "Project Name",
      "plot_range": {"start": 1, "end": 100},
      "linked_contacts": "contact1@example.com, contact2@example.com",
      "google_sheet_url_windows": "https://docs.google.com/spreadsheets/d/...",
      "google_sheet_url_carpentry": "https://docs.google.com/spreadsheets/d/..."
    }
  ],
  "misc_sheet_url": "https://docs.google.com/spreadsheets/d/...",
  "project_types": [
    {"name": "windows", "day_rate": 200.0, "hour_rate": 25.0, "keywords": "window, glass"},
    {"name": "carpentry", "day_rate": 250.0, "hour_rate": 30.0, "keywords": "door, cabinet"}
  ]
}
```

## How It Works

1. Monitors inbox for unread emails (checks every 5 seconds)
2. Uses GPT to extract email details (company, topic, items, project info)
3. Determines forwarding recipient based on topic
4. For "order" and "variation" emails:
   - Matches email to project
   - Adds items to Google Sheets
   - Saves email and attachments to Google Drive
   - Links Drive folder back to sheet
5. Forwards email with enhanced subject line

## Google Drive Setup

Update `MAIN_FOLDER_ID` in `internal/gdrive.py` with your Google Drive folder ID. Ensure the service account has edit access.

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `GOOGLE_SERVICE_ACCOUNT_KEY_JSON`: Google Service Account JSON key
