from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your secret key

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root@localhost/barber_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    dob = db.Column(db.String(10), nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Define the Appointment model
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(150), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False)
    service = db.Column(db.String(150), nullable=False)

# Create the database and the tables
with app.app_context():
    db.create_all()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json()
        if data is None:
            return jsonify({'message': 'Invalid JSON data'}), 400
        
        name = data.get('name')
        email = data.get('email')
        dob = data.get('dob')
        password = data.get('password')

        if not name or not email or not dob or not password:
            return jsonify({'message': 'All fields are required'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'message': 'Email already exists'}), 400

        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(name=name, email=email, dob=dob, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({'message': 'User registered successfully', 'redirect_url': url_for('login')}), 201

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'message': 'Email and password are required'}), 400

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            return jsonify({'message': 'Invalid email or password'}), 400

        session['user_id'] = user.id
        return jsonify({'message': 'Logged in successfully', 'redirect_url': url_for('dashboard')}), 200

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/book_appointment')
def book_appointments():
    return render_template('book_appointment.html')

@app.route('/api/available_slots', methods=['POST'])
def available_slots():
    data = request.get_json()
    date = datetime.strptime(data['date'], '%Y-%m-%d')
    duration = data['duration']
    
    # Generate all possible slots for the day (9 AM to 6 PM)
    start_time = datetime.combine(date, datetime.strptime('09:00', '%H:%M').time())
    end_time = datetime.combine(date, datetime.strptime('18:00', '%H:%M').time())
    slot_duration = timedelta(minutes=duration)
    
    slots = []
    current_time = start_time
    
    while current_time + slot_duration <= end_time:
        slots.append(current_time.strftime('%H:%M'))
        current_time += slot_duration
    
    # Filter out slots that are already taken
    booked_slots = [datetime.strptime(app['date_time'], '%Y-%m-%d %H:%M') for app in appointments if app['date_time'].startswith(data['date'])]
    available_slots = [slot for slot in slots if all(abs((datetime.combine(date, datetime.strptime(slot, '%H:%M').time()) - bs).total_seconds()) >= duration * 60 for bs in booked_slots)]
    
    return jsonify(available_slots)



@app.route('/api/appointments')
@login_required
def get_appointments():
    appointments = Appointment.query.order_by(Appointment.date_time).all()
    appointments_list = [{
        'client_name': appointment.client_name,
        'date_time': appointment.date_time.strftime('%B %d, %Y at %I:%M %p'),
        'service': appointment.service
    } for appointment in appointments]
    return jsonify(appointments_list)

@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
