# app.py
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_session import Session  # new import
from sqlalchemy.exc import OperationalError
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import requests
import random
import atexit
import pytz
import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
session_lifetime_minutes = int(os.getenv('SESSION_LIFETIME_MINUTES', 30))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=session_lifetime_minutes)
timezone_str = os.getenv('TZ', 'UTC')  # Default to 'UTC' if not set
local_timezone = pytz.timezone(timezone_str)

# Configure Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'
session_dir = os.path.join(os.getcwd(), 'sessions')
os.makedirs(session_dir, exist_ok=True)
app.config['SESSION_FILE_DIR'] = session_dir
Session(app)

API_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
SCHEDULE_UNIT = os.getenv("SCHEDULE_UNIT")
SCHEDULE_VALUE = int(os.getenv("SCHEDULE_VALUE"))

db = SQLAlchemy(app)

# Model for storing sessions and guesses
class RVSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    unique_identifier = db.Column(db.String(10), unique=True, nullable=False)
    user_guess = db.Column(db.Text, nullable=True)
    rating = db.Column(db.Integer)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(local_timezone))


def delete_old_entries():
    with app.app_context():
        db.session.query(RVSession).filter(
            (RVSession.rating == 1) & (RVSession.created_date <= datetime.now(local_timezone) - timedelta(**{SCHEDULE_UNIT: SCHEDULE_VALUE}))
        ).delete()
        db.session.commit()


def generate_unique_id():
    while True:
        # Randomly choose the format
        format_choice = random.choice([1, 2, 3])
        
        if format_choice == 1:
            part1 = random.randint(1000, 9999)
            part2 = random.randint(1000, 9999)
        elif format_choice == 2:
            part1 = random.randint(100, 999)
            part2 = random.randint(1000, 9999)
        else:
            part1 = random.randint(1000, 9999)
            part2 = random.randint(10, 99)
            
        unique_id = f"{part1}-{part2}"
        
        # Check if this ID already exists in the database
        existing = RVSession.query.filter_by(unique_identifier=unique_id).first()
        if not existing:
            return unique_id


# Fetch random image URL (using Unsplash as an example)
def fetch_random_image():
    try:
        response = requests.get('https://api.unsplash.com/photos/random', headers={'Authorization': f'Client-ID {API_KEY}'})
        response.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code.
        
        # Check if the expected data is present in the response
        image_url = response.json().get('urls', {}).get('regular')
        if not image_url:
            raise ValueError("Image URL not found in the API response")
        
        return image_url
    
    except requests.RequestException as e:
        # Handle any kind of requests exception (like timeouts, connection errors, etc.)
        print(f"Error fetching image from Unsplash: {e}")
        return None
    except ValueError as e:
        # Handle missing expected data
        print(e)
        return None


def delete_empty_user_guess_sessions():
    sessions_to_delete = RVSession.query.filter(
        (RVSession.user_guess == None) | (RVSession.user_guess == "")
    ).all()
    for session_to_delete in sessions_to_delete:
        db.session.delete(session_to_delete)
    db.session.commit()


@app.route('/')
def index():
    delete_empty_user_guess_sessions()
    return render_template('index.html')


@app.route('/start_session', methods=['POST'])
def start_session():
    name = request.form.get('name')
    
    if not name or not name.strip():
        flash('Name cannot be empty', 'error')
        return redirect(url_for('index'))

    image_url = fetch_random_image()
    if not image_url:
        flash('Error fetching the image. Please try again later.', 'error')
        return redirect(url_for('index'))
    
    unique_id = generate_unique_id()
    new_session = RVSession(name=name.strip(), image_url=image_url, unique_identifier=unique_id)
    db.session.add(new_session)
    db.session.commit()
    session['current_id'] = new_session.id
    return render_template('session.html', unique_id=unique_id)



@app.route('/submit_guess', methods=['POST'])
def submit_guess():
    user_guess = request.form.get('guess')
    current_session_id = session.get('current_id')

    # Attempt to retrieve the session using the session ID
    current_session = RVSession.query.get(current_session_id) if current_session_id else None

    # If session is not found, try retrieving the last session based on the user's name
    if not current_session:
        name = request.form.get('name')
        if name:
            current_session = RVSession.query.filter_by(name=name.strip()).order_by(RVSession.created_date.desc()).first()

    # If no session is found, prompt to start a new session
    if not current_session:
        flash('No active session found. Please start a new session.', 'error')
        return redirect(url_for('index'))

    # Process the user guess
    if user_guess and user_guess.strip():
        current_session.user_guess = user_guess.strip()
        db.session.commit()
        flash('Guess submitted successfully!', 'success')
    else:
        flash('Please enter a guess before submitting.', 'error')

    return redirect(url_for('reveal_image'))



@app.route('/reveal_image')
def reveal_image():
    current_session = RVSession.query.get(session['current_id'])
    return render_template('reveal.html', image_url=current_session.image_url, guess=current_session.user_guess, rating=current_session.rating)


@app.route('/view_results')
def view_results():
    sort_by = request.args.get('sort_by', 'created_date')
    sort_direction = request.args.get('direction', 'desc')

    if sort_by not in ['name', 'unique_identifier', 'user_guess', 'rating', 'created_date']:
        sort_by = 'created_date'

    if sort_direction not in ['asc', 'desc']:
        sort_direction = 'desc'

    # Apply sorting based on the parameters
    if sort_direction == 'asc':
        all_sessions = RVSession.query.order_by(getattr(RVSession, sort_by).asc())
    else:
        all_sessions = RVSession.query.order_by(getattr(RVSession, sort_by).desc())

    delete_empty_user_guess_sessions()

    return render_template('results.html', sessions=all_sessions, sort_by=sort_by, sort_direction=sort_direction)


@app.route('/view_image/<int:session_id>')
def view_image(session_id):
    current_session = RVSession.query.get(session_id)
    if current_session is None:
        flash('The image session you are trying to view does not exist. It may have been deleted.', 'error')
        return redirect(url_for('view_results'))
    return render_template('view_image.html', image_url=current_session.image_url, current_session=current_session)


@app.route('/rate_image', methods=['POST'])
def rate_image():
    current_session = RVSession.query.get(session['current_id'])
    rating = int(request.form.get('rating'))
    current_session.rating = rating
    db.session.commit()
    flash('Image rated successfully!', 'success')
    return redirect(url_for('index'))


@app.route('/update_rating/<int:session_id>', methods=['POST'])
def update_rating(session_id):
    current_session = RVSession.query.get(session_id)
    if current_session is None:
        # If the session does not exist, redirect back to the results with a message
        flash('The session you attempted to rate does not exist. It may have been deleted.', 'error')
        return redirect(url_for('view_results'))

    new_rating = int(request.form.get('rating'))
    current_session.rating = new_rating
    db.session.commit()
    flash('Rating updated successfully!', 'success')
    return redirect(url_for('view_results'))  # Redirecting to view_results instead of view_image

scheduler = BackgroundScheduler()
scheduler.add_job(func=delete_old_entries, trigger="interval", **{SCHEDULE_UNIT: SCHEDULE_VALUE})
scheduler.start()
atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    # create db if not exists
    try:
        db.create_all()
    except OperationalError as e:
        print(f"Error creating database: {e}")

