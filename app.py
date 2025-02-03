from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from dotenv import load_dotenv
import os
load_dotenv()
print(os.getenv('DATABASE_URL'))
print(os.getenv('SECRET_KEY'))
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class UserData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    liked_movies = db.Column(db.Text, nullable=True)
    disliked_movies = db.Column(db.Text, nullable=True)

# Cache the similarity matrix
data, sim = None, None

def create_sim():
    global data, sim
    if data is None or sim is None:
        data = pd.read_csv('data.csv')
        cv = CountVectorizer()
        count_matrix = cv.fit_transform(data['comb'])
        sim = cosine_similarity(count_matrix)
    return data, sim

def rcmd(m, liked_movies, disliked_movies):
    m = m.lower()
    data, sim = create_sim()
    if m not in data['movie_title'].unique():
        return 'This movie is not in our database. Please check if you spelled it correctly.'
    else:
        i = data.loc[data['movie_title'] == m].index[0]
        lst = list(enumerate(sim[i]))
        lst = sorted(lst, key=lambda x: x[1], reverse=True)
        lst = lst[1:11]
        recommendations = [data['movie_title'][lst[i][0]] for i in range(len(lst))]
        # Remove disliked movies from recommendations
        recommendations = [movie for movie in recommendations if movie not in disliked_movies]
        # Ensure no duplicates and include liked movies
        recommendations = list(dict.fromkeys(recommendations + liked_movies))
        return recommendations

def init_db():
    """Initialize the database and create tables if they don't exist."""
    with app.app_context():
        db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
        else:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['username'] = username
            return redirect(url_for('recommend'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/recommend', methods=['GET', 'POST'])
def recommend():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    user_data = UserData.query.filter_by(username=username).first()
    liked_movies = user_data.liked_movies.split(',') if user_data and user_data.liked_movies else []
    disliked_movies = user_data.disliked_movies.split(',') if user_data and user_data.disliked_movies else []

    if request.method == 'POST':
        movie = request.form['movie']
        recommendations = rcmd(movie, liked_movies, disliked_movies)
        if isinstance(recommendations, str):
            flash(recommendations, 'danger')
        else:
            return render_template(
                'recommend.html', 
                recommendations=recommendations, 
                liked_movies=liked_movies, 
                disliked_movies=disliked_movies
            )
    return render_template('recommend.html', liked_movies=liked_movies, disliked_movies=disliked_movies)

@app.route('/like_movie', methods=['POST'])
def like_movie():
    movie = request.form['movie']
    username = session['username']
    user_data = UserData.query.filter_by(username=username).first()
    
    if user_data:
        liked_movies = user_data.liked_movies.split(',') if user_data.liked_movies else []
        disliked_movies = user_data.disliked_movies.split(',') if user_data.disliked_movies else []
        
        if movie in disliked_movies:
            disliked_movies.remove(movie)
            user_data.disliked_movies = ','.join(disliked_movies)
        
        if movie not in liked_movies:
            liked_movies.append(movie)
            user_data.liked_movies = ','.join(liked_movies)
        
        db.session.commit()
    else:
        new_user_data = UserData(username=username, liked_movies=movie)
        db.session.add(new_user_data)
        db.session.commit()
        
    return redirect(url_for('recommend'))

@app.route('/dislike_movie', methods=['POST'])
def dislike_movie():
    movie = request.form['movie']
    username = session['username']
    user_data = UserData.query.filter_by(username=username).first()
    
    if user_data:
        liked_movies = user_data.liked_movies.split(',') if user_data.liked_movies else []
        disliked_movies = user_data.disliked_movies.split(',') if user_data.disliked_movies else []
        
        if movie in liked_movies:
            liked_movies.remove(movie)
            user_data.liked_movies = ','.join(liked_movies)
        
        if movie not in disliked_movies:
            disliked_movies.append(movie)
            user_data.disliked_movies = ','.join(disliked_movies)
        
        db.session.commit()
    else:
        new_user_data = UserData(username=username, disliked_movies=movie)
        db.session.add(new_user_data)
        db.session.commit()
        
    return redirect(url_for('recommend'))
@app.route('/modify_list', methods=['POST'])
def modify_list():
    movie = request.form['movie']
    action = request.form['action']
    username = session['username']
    user_data = UserData.query.filter_by(username=username).first()
    
    if user_data:
        liked_movies = user_data.liked_movies.split(',') if user_data.liked_movies else []
        disliked_movies = user_data.disliked_movies.split(',') if user_data.disliked_movies else []
        
        if action == 'like':
            if movie in disliked_movies:
                flash('You cannot like a movie that is already disliked.', 'danger')
            elif movie not in liked_movies:
                liked_movies.append(movie)
                user_data.liked_movies = ','.join(liked_movies)
                db.session.commit()
        elif action == 'dislike':
            if movie in liked_movies:
                flash('You cannot dislike a movie that is already liked.', 'danger')
            elif movie not in disliked_movies:
                disliked_movies.append(movie)
                user_data.disliked_movies = ','.join(disliked_movies)
                db.session.commit()
        elif action == 'remove_like':
            if movie in liked_movies:
                liked_movies.remove(movie)
                user_data.liked_movies = ','.join(liked_movies)
                db.session.commit()
        elif action == 'remove_dislike':
            if movie in disliked_movies:
                disliked_movies.remove(movie)
                user_data.disliked_movies = ','.join(disliked_movies)
                db.session.commit()
        
    return redirect(url_for('recommend'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=8000)