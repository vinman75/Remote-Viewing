# Remote Viewing Application

## Overview

Remote Viewing is a simple web-based tool for practising remote viewing. Users predict the content of a specific image from Unsplash, which is determined by a pre-set associated number before revealment, ensuring consistency in the remote viewing experience.

## Screenshots

![App Example](screen_shots/start.png)
![App Example](screen_shots/session.png)
![App Example](screen_shots/reveal.png)
![App Example](screen_shots/results.png)

## Installation

1. Ensure Python 3.10 or above is installed.
2. Install the required packages:
```
pip install -r requirements.txt
```

## API Configuration

To use the application, you need to set up the environment with your API keys and configuration details.

### Initial Setup

1. Obtain a free Unsplash API developer account at [Unsplash Developers](https://unsplash.com/developers).

2. Create a copy of the `.env.example` file and rename it to `.env`.

3. Open the `.env` file and fill in your Unsplash API Access Key where it says `YOUR_UNSPLASH_ACCESS_KEY_HERE`.

4. Generate a secure Flask secret key and add it to the `.env` file in place of `YOUR_FLASK_SECRET_KEY_HERE`. This key is important for maintaining session security.

5. Define the clean-up schedule by setting `SCHEDULE_UNIT` (like 'minutes', 'hours', etc.) and `SCHEDULE_VALUE` (an integer) to determine how often old entries should be deleted.

### Time Zone Configuration

- In `.env`, set the `TIMEZONE` variable to your local time zone, for example, `TIMEZONE='America/New_York'`. This will ensure that the application uses your local time zone for all operations. If you do not set this variable, it will default to 'UTC'.

### Final Steps

After configuring your `.env` file with the API key, secret key, schedule, and time zone settings, you're ready to start the application.



## Launching

Navigate to the directory containing `app.py` and run:
```
python app.py
```

## Features

- **User Sessions**: Initiate with a name.
- **Image Retrieval**: Random images sourced from Unsplash.
- **Guess Submission**: Users store their predictions.
- **Reveal and Score**: Users view the actual image and self-rate.
- **Result Logs**: Review past sessions.
- **Auto Cleanup**: Periodically deletes old low-rated entries based on settings.

## Background Scheduler

The application includes a scheduler that deletes old sessions with a rating of 1 after a specified duration. This can be configured using `SCHEDULE_UNIT` and `SCHEDULE_VALUE`, which can be adjusted in your `.env` file.


## Deployment

For production on Linux, serve using gunicorn:

### Start with Gunicorn

```sh
gunicorn wsgi:app --bind 0.0.0.0:5000 -w 4 --timeout 300
```

To start the application in the background using `nohup`:

```sh
nohup gunicorn wsgi:app --bind 0.0.0.0:5000 -w 4 --timeout 300 > output.log 2>&1 &
```

### Worker and Timeout Notes

- `-w` defines worker processes. Adjust based on load and resources.
- `--timeout` defines seconds before worker restart. Ensure it exceeds the maximum duration of the `delete_old_entries` function.

### WSGI Configuration

The `wsgi.py` file is set up to handle proxy servers and ensures secure connections with HTTPS. If required, you can adjust the default port for Flask, which is 5000.

```python
from werkzeug.middleware.proxy_fix import ProxyFix
from app import app

app.config['PREFERRED_URL_SCHEME'] = 'https'
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Change port if required: default is 5000 for flask
if __name__ == '__main__':
    app.run(debug=False, port=5000)

# create a WSGI application object
application = app
```

### Stopping

Kill the gunicorn process:
```
pkill gunicorn
```
