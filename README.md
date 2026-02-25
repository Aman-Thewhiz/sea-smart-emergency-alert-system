<<<<<<< HEAD
# SMART EMERGENCY ALERT SYSTEM

Developer: Aman Kumar  
Team: Apex Labs  
University: SRM University-AP

A production-ready emergency alert system that sends email and SMS alerts with live GPS location, stores alert history, and provides real-time tracking on a professional dashboard.

## Features

- Emergency alert button with live GPS capture
- Email alerts with Google Maps link
- SMS alerts via Twilio
- Live tracking every 5 seconds with path history
- Alerts and tracking stored in SQLite
- Alert history dashboard and dedicated history page
- Health check endpoint for monitoring
- Rate limiting and structured logging

## Tech Stack

- Backend: Flask, SQLite, Twilio, SMTP
- Frontend: HTML5, CSS3, Vanilla JS, Leaflet.js
- Deployment: Gunicorn compatible

## Project Structure

```
/sea-project
  /static
    style.css
    script.js
  /templates
    index.html
    history.html
  app.py
  requirements.txt
  .env.example
  README.md
```

## Setup

1. Create a virtual environment and install dependencies:

```
pip install -r requirements.txt
```

2. Create a `.env` file in the project root and add your configuration (see `.env.example`).

## Environment Variables

Required:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASS`
- `EMERGENCY_EMAIL_FROM`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER`

Optional:

- `DEFAULT_COUNTRY` (default: IN)
- `RATE_LIMIT_WINDOW_SECONDS` (default: 60)
- `RATE_LIMIT_MAX` (default: 5)
- `PORT` (default: 5000)
- `LOG_LEVEL` (default: INFO)
- `LOG_FILE` (empty means stdout only)

## Run Locally

```
python app.py
```

Open http://127.0.0.1:5000

## Production Deployment

Using Gunicorn:

```
gunicorn -c gunicorn_conf.py wsgi:app
```

## API Endpoints

- `POST /send_alert`
- `GET /get_alerts`
- `POST /update_location`
- `GET /get_tracking_history`
- `GET /health`

## Notes

- Alerts are stored in `alerts.db` automatically.
- Live tracking is stored in the `tracking` table and displayed on the map.
- Email and SMS are both required for a successful alert delivery.
=======
# SMART EMERGENCY ALERT SYSTEM

Developer: Aman Kumar  
Team: Apex Labs  
University: SRM University-AP

A production-ready emergency alert system that sends email and SMS alerts with live GPS location, stores alert history, and provides real-time tracking on a professional dashboard.

## Features

- Emergency alert button with live GPS capture
- Email alerts with Google Maps link
- SMS alerts via Twilio
- Live tracking every 5 seconds with path history
- Alerts and tracking stored in SQLite
- Alert history dashboard and dedicated history page
- Health check endpoint for monitoring
- Rate limiting and structured logging

## Tech Stack

- Backend: Flask, SQLite, Twilio, SMTP
- Frontend: HTML5, CSS3, Vanilla JS, Leaflet.js
- Deployment: Gunicorn compatible

## Project Structure

```
/sea-project
  /static
    style.css
    script.js
  /templates
    index.html
    history.html
  app.py
  requirements.txt
  .env.example
  README.md
```

## Setup

1. Create a virtual environment and install dependencies:

```
pip install -r requirements.txt
```

2. Create a `.env` file in the project root and add your configuration (see `.env.example`).

## Environment Variables

Required:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASS`
- `EMERGENCY_EMAIL_FROM`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER`

Optional:

- `DEFAULT_COUNTRY` (default: IN)
- `RATE_LIMIT_WINDOW_SECONDS` (default: 60)
- `RATE_LIMIT_MAX` (default: 5)
- `PORT` (default: 5000)
- `LOG_LEVEL` (default: INFO)
- `LOG_FILE` (empty means stdout only)

## Run Locally

```
python app.py
```

Open http://127.0.0.1:5000

## Production Deployment

Using Gunicorn:

```
gunicorn -c gunicorn_conf.py wsgi:app
```

## API Endpoints

- `POST /send_alert`
- `GET /get_alerts`
- `POST /update_location`
- `GET /get_tracking_history`
- `GET /health`

## Notes

- Alerts are stored in `alerts.db` automatically.
- Live tracking is stored in the `tracking` table and displayed on the map.
- Email and SMS are both required for a successful alert delivery.
>>>>>>> 9ff4e1b8de1c80ab4df041ad2aa60eacb793586e
