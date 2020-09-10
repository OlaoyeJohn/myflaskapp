from flask import Flask, render_template, flash, request, redirect, jsonify, make_response, url_for, session, logging

from data import CsvFiles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import os
import csv
import pandas as pd
import numpy as np
import sqlalchemy
import pickle
from flask_migrate import Migrate






app = Flask(__name__)

model= pickle.load(open('model.pkl','rb'))


# config my sql
app.config['MYSQL_HOST'] = 'ec2-54-204-26-236.compute-1.amazonaws.com'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '6876463bb34f435637f4cce7b7d05347bab636dda0d6955ccc1e96a1f06ff999'
app.config['MYSQL_DB'] = 'db3u50742op9k3'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

app.config['SECRET_KEY'] = "Pass1234"
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False

engine = sqlalchemy.create_engine("postgres://ifbvgdtixghczw:6876463bb34f435637f4cce7b7d05347bab636dda0d6955ccc1e96a1f06ff999@ec2-54-204-26-236.compute-1.amazonaws.com:5432/db3u50742op9k3")


# init MYSQL
mysql = MySQL(app)

# init Postgres
migrate = Migrate(app)


CsvFiles = CsvFiles()

#Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unathorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

#Home
@app.route("/")
def index():
    return render_template("home.html")

#About
@app.route("/about")
def about():
    return render_template("about.html")

#Contact
@app.route("/contact")
def contact():
    return render_template("contact.html")

#Files
@app.route("/csv_files")
def csv_files():
    return render_template("csv_files.html", csv_files=CsvFiles)

#Single file uploaded
@app.route("/csv_file/<string:id>/")
def csv_file(id):
    return render_template("csv_file.html", id=id)

#Class Register Form
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=50)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [validators.DataRequired(
    ), validators.EqualTo('confirm', message='Password do not match')])
    confirm = PasswordField('Confirm Password')

#Obtaining Data Register Form
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # create cursor
        cur = migrate.connection.cursor()

        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)",
                    (name, email, username, password))

        # commit to DB
        migrate.connection.commit()

        # close connection
        cur.close()

        flash('You are now register and can log in', 'success')

        return redirect(url_for('login'))

        return render_template('register.html',form=form)

    return render_template('register.html', form=form)

# user Login
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # database cursor

        cur = migrate.connection.cursor()

        # get user by username
        result = cur.execute(
            "SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # get stored hash
            data = cur.fetchone()
            password = data['password']

            # compare password
            if sha256_crypt.verify(password_candidate, password):
                # paased
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid Login'
                return render_template('login.html', error=error)
                
            # close connection
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template("login.html")




#Log out
@app.route('/logout')
def logout():
    session.clear()
    flash('You are logged out', 'success')
    return redirect(url_for('login'))


#Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    return render_template('/dashboard.html')


#Dataset used to train our Model
@app.route('/table')
def table():
    return render_template('/table.html')



# Uploads path
app.config['CSV_FILES'] = '/static/Uploads/'

#upload CSV File
@app.route("/add_file", methods=["GET", "POST"])
@is_logged_in
def add_file():

    if request.method == "POST":

        if request.files:

            csv = (request.files["csv"])
            csv.save(os.path.join(app.config['CSV_FILES'],csv.filename))
            file_path= '/static/Uploads/'+csv.filename
            with open(file_path, 'r') as csv_file:
                data = pd.read_csv(csv_file)

                
                data.to_sql(
                    name='trialdata_tbl',
                    con=engine,
                    index=False,
                    if_exists='replace'
                )
            
            return redirect(url_for('predict'))


    return render_template("add_file.html")

#prediction route
@app.route('/predict', methods=['GET','POST'])
@is_logged_in
def predict():

    uploaded_file = pd.read_sql_table('trialdata_tbl',engine)

    prediction = model.predict(uploaded_file)

    if prediction == 0:
        result = 'I predict this is a GOOD TRANSACTION'
        return render_template('/predict.html', prediction_text=result)
        # flash('The Transaction is a credible one')

    elif prediction == 1:
        result = 'I suspect this is a FRAUDULENT TRANSACTION'
        return render_template('/predict.html', prediction_text=result)
        # flash('The Transaction is a suspected FRAUD TRANSACTION')
    else:
        print('I am still training.')
        
    return render_template('/predict.html', prediction_text=prediction)


if __name__ == "__main__":
    app.secret_key = "Pass1234"
    app.run(debug=True)
