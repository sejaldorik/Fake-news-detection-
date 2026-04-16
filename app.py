import os
from flask import Flask, render_template, url_for, flash, redirect, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from flask_wtf.csrf import CSRFProtect
from database import db, User, History
from forms import RegistrationForm, LoginForm
from utils import MLEngine, extract_text_from_url, extract_text_from_pdf
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = 'uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db.init_app(app)
csrf = CSRFProtect(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

ml_engine = MLEngine()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_request
def create_tables():
    app.before_request_funcs[None].remove(create_tables)
    db.create_all()

@app.route("/", methods=['GET', 'POST'])
@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('detection'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('detection'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/detection")
@login_required
def detection():
    return render_template('detection.html', title='Detection')

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template('dashboard.html', title='Dashboard')

@app.route("/api/predict", methods=['POST'])
@login_required
def predict():
    if not ml_engine.is_loaded:
        ml_engine.__init__() # Try to load again
        if not ml_engine.is_loaded:
            return jsonify({'error': 'Model is not trained/loaded yet. Please run train_model.py.'}), 500
        
    input_type = request.form.get('inputType')
    input_text = ""
    
    if input_type == 'text':
        input_text = request.form.get('textInput')
        if not input_text:
            return jsonify({'error': 'No text provided'}), 400
            
    elif input_type == 'url':
        url = request.form.get('urlInput')
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        input_text = extract_text_from_url(url)
        if not input_text:
            return jsonify({'error': 'Could not extract text from URL'}), 400
            
    elif input_type == 'pdf':
        if 'pdfInput' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['pdfInput']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        if file and file.filename.endswith('.pdf'):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            input_text = extract_text_from_pdf(filepath)
            os.remove(filepath) # clean up
            if not input_text:
                return jsonify({'error': 'Could not extract text from PDF'}), 400
        else:
            return jsonify({'error': 'Invalid file type. Only PDF allowed.'}), 400
    else:
        return jsonify({'error': 'Invalid input type'}), 400

    # Ensure input_text is not too long for the DB preview
    snippet = input_text[:500] + "..." if len(input_text) > 500 else input_text
    
    # Predict
    result = ml_engine.predict(input_text)
    if "error" in result:
        return jsonify(result), 500
        
    # Save History
    h = History(
        user_id=current_user.id,
        input_type=input_type,
        input_content=snippet,
        prediction=result['prediction'],
        confidence=result['confidence']
    )
    db.session.add(h)
    db.session.commit()
    
    return jsonify(result)

@app.route("/api/dashboard_data")
@login_required
def dashboard_data():
    histories = History.query.filter_by(user_id=current_user.id).order_by(History.timestamp.desc()).all()
    
    data = []
    fake_count = 0
    true_count = 0
    timeline = {}
    
    for h in histories:
        # Basic stats
        if h.prediction == 'Fake':
            fake_count += 1
        else:
            true_count += 1
            
        # Timeline
        date_str = h.timestamp.strftime('%Y-%m-%d')
        if date_str not in timeline:
            timeline[date_str] = {'Fake': 0, 'True': 0}
        timeline[date_str][h.prediction] += 1
        
        # History Array
        data.append({
            'id': h.id,
            'input_type': h.input_type,
            'snippet': h.input_content,
            'prediction': h.prediction,
            'confidence': h.confidence,
            'timestamp': h.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    return jsonify({
        'history': data,
        'stats': {
            'fake': fake_count,
            'true': true_count,
            'total': fake_count + true_count
        },
        'timeline': timeline
    })

if __name__ == '__main__':
    app.run(debug=True)
