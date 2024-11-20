import os, requests, pytz
from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'images')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
db = SQLAlchemy(app)
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1306892506063179807/VuQlEflMglRaw2grRaOGMXYOwdqoJKmeh_Fhj_RYCAENj7zHF6EJIBbqRzLijPej5FVd"

# Get WIB time used for logging
def get_wib_time():
    wib = pytz.timezone('Asia/Jakarta')
    now = datetime.now(wib)
    return now.replace(microsecond=0)

# User table
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), unique=True, nullable=False)
    user_bio = db.Column(db.String(400))
    user_profile = db.Column(db.String, nullable=True)
    images = db.relationship('Image', backref='user', cascade='all, delete')
    session = db.relationship('UserSession', backref='user', cascade='all, delete')

# Image table
class Image(db.Model):
    id_image = db.Column(db.Integer, primary_key=True, unique=True)
    id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    title = db.Column(db.String(100), nullable=False)
    image_filename = db.Column(db.String, nullable=False)

# Session table
class UserSession(db.Model):
    id_session = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    login_time = db.Column(db.DateTime, default=get_wib_time)
    logout_time = db.Column(db.DateTime, nullable=True)
    userlogs = db.relationship('Logs', backref='session', lazy=True)

# Logs table
class Logs(db.Model):
    id_log = db.Column(db.Integer, primary_key=True, unique=True)  
    id_session = db.Column(db.Integer, db.ForeignKey('user_session.id_session'))
    time = db.Column(db.DateTime, default=get_wib_time)
    log_message = db.Column(db.String(500))

# Check file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

with app.app_context():
    db.create_all()

# Init route
@app.route('/')
def index():
    getImages = Image.query.all()
    return render_template('index.html', images=getImages)

# Sign in
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        userbiodata = 'No info!'
        hashed_password = generate_password_hash(password)
        
        # Check if username exists
        user = User.query.filter_by(username=username).first()
        if user:
            flash("Username already exists. Try another one.")
            return redirect(url_for('signin'))
        
        new_user = User(username=username, password=hashed_password, user_bio=userbiodata, user_profile="300.png")
        db.session.add(new_user)
        db.session.commit()
        
        flash("Signup successful! Please log in.")
        return redirect(url_for('login'))
    return render_template('signin.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_time = get_wib_time()
            user_session = UserSession(id=user.id, login_time=login_time)
            db.session.add(user_session)
            db.session.commit()
            session['user_id'] = user.id
            session['session_id'] = user_session.id
            login_success = f"User {username} Has Successfully Logged In!"
            process_log(login_success)
            return redirect(url_for('userdashboard', username=username))
        else:
            return redirect(url_for('signin'))
    return render_template('login.html')

# User dashboard
@app.route('/dashboarduser/<string:username>')
def userdashboard(username):
    if 'user_id' not in session:
        flash("You need to log in first.")
        return redirect(url_for('login'))
    id = session['user_id']
    getuser = User.query.get_or_404(id)
    getImages = Image.query.filter_by(id=id).all()
    return render_template('userpage.html', user=getuser, images=getImages)
        
# User Edit Data
@app.route('/dashboard/<string:username>/edit', methods=['GET', 'POST'],) 
def edituser(username):
    if request.method == 'POST' or 'GET':
        getuser = User.query.get_or_404(session['user_id'])
        getusername = User.query.filter_by(username=getuser.username)
        log_msg = f"User {getuser.username} has edited their profile! The changes are : "
    
        file = request.files['profile']
        # Check profile picture file
        if file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)  # Sanitize filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            getuser.user_profile = filename
            db.session.commit()
            log_msg += f"Profile Picture from '{getuser.user_profile}' => '{filename}', "
        elif file.filename != '' and allowed_file(file.filename) is not True:
            flash('Invalid Profile!')
            return redirect(url_for('userdashboard', username=username))
        # Check Username and Bio changes
        if getusername is True and getusername.id != getuser.id:
            flash("This Username already exist")
            return redirect(url_for('userdashboard', username=username))
        if request.form['username'] == getuser.username :
            log_msg += f"Username unchanged, "
        else :
            log_msg += f"Username has been changed from '{getuser.username}' => '{request.form['username']}', "
        if request.form['bio'] == getuser.user_bio :
            log_msg += f"Bio unchanged."
        else :
            log_msg += f"Bio has been changed from '{getuser.user_bio}' to => '{request.form['bio']}'."
            
        getuser.username = request.form['username']
        getuser.user_bio = request.form['bio']
        db.session.commit()
        process_log(log_msg)
        flash("Data Edited Successfully")
        return redirect(url_for('userdashboard', username=username))

# user logout
@app.route('/logout')
def logout():
    session_id = session.get('session_id')
    if session_id:
        # Log end session to database
        user_session_end = UserSession.query.get(session_id)
        user_session_end.logout_time = get_wib_time()
        db.session.commit()
        
        # Output Logout Log Msg
        getuser = User.query.get_or_404(session['user_id'])
        logout_msg = f"User {getuser.username} Has Logged Out!"
        process_log(logout_msg)
        session.clear()
        return redirect(url_for('index'))
    return redirect(url_for('userdashboard', username=getuser.username))
    
# Upload Image
@app.route('/dashboard/<string:username>/uploadimage', methods=['POST'])
def uploadimage(username):
    if request.method == 'POST':
        file = request.files['image_upload']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)  # Sanitize filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Save the filename in the database
            imagetitle = request.form['title']
            new_image = Image(id=session['user_id'], title=imagetitle, image_filename=filename)
            db.session.add(new_image)
            db.session.commit()
            get_user = User.query.get_or_404(session['user_id'])
            process_log(f"User {get_user.username} Has Uploaded Image ['{filename}'] With Title ['{imagetitle}']!")
            return redirect(url_for('userdashboard', username=username))
    return redirect(url_for('userdashboard', username=username))

# Delete image
@app.route('/dashboard/<string:username>/deleteimage/<int:id_image>')
def deleteimage(username, id_image):
    get_image = Image.query.get(id_image)
    if get_image:
        image_name = get_image.image_filename
        db.session.delete(get_image) 
        db.session.commit()    
        process_log(f"User {username} has Successfully deleted an Image! (Image = '{image_name}')")
        return redirect(url_for('userdashboard', username=username))
    else:
        process_log(f"User {username} has failed to delete an Image!")
        return redirect(url_for('userdashboard', username=username)) 
            
# Logging function
def process_log(message):
    log_to_db = Logs(id_session=session['session_id'], log_message=message)
    db.session.add(log_to_db)
    db.session.commit()
    newest_log = Logs.query.filter_by(id_session=session['session_id']).first()
    
    payload = {
        "content": f"[**{newest_log.time}**]: {message}",
    }
    response = requests.post(DISCORD_WEBHOOK, json=payload)
    if response.status_code != 204:
        print(f"Failed to send message to Discord: {response.status_code} {response.text}")

if __name__ == '__main__':
    db.create_all
    app.run(host="0.0.0.0", port=5000)
    app.run(debug=True)
