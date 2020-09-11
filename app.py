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
import psycopg2






app = Flask(__name__)

model= pickle.load(open('model.pkl','rb'))


# config my sql
app.config['MYSQL_HOST'] = 'ec2-54-204-26-236.compute-1.amazonaws.com'
app.config['MYSQL_USER'] = 'ifbvgdtixghczw'
app.config['MYSQL_PASSWORD'] = '6876463bb34f435637f4cce7b7d05347bab636dda0d6955ccc1e96a1f06ff999'
app.config['MYSQL_DB'] = 'db3u50742op9k3'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

app.config['SECRET_KEY'] = "Pass1234"
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False

conn = psycopg2.connect(
    database="db3u50742op9k3",
    user="ifbvgdtixghczw",
    password="6876463bb34f435637f4cce7b7d05347bab636dda0d6955ccc1e96a1f06ff999",
    host="ec2-54-204-26-236.compute-1.amazonaws.com",
    port='5432'
)

# init MYSQL
mysql = MySQL(app)

# init Postgres
# migrate = Migrate(app)


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
        cur = conn.cursor()
        # cur = migrate.connection.cursor()

        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)",
                    (name, email, username, password))

        # commit to DB
        conn.commit()

        # close connection
        cur.close()

        flash('You are now register and can log in', 'success')

        return redirect(url_for('login'))

        return render_template('register.html',form=form)

    return render_template('register.html', form=form)


## New code trying out start
@app.route("/login", methods=["POST","GET"])
def login():
    if request.method == 'POST':
        return render_template("login.html", t_message = "Login here")
        username = request.form.get("username", "")
        password_candidate = request.form.get("password", "")

    # VALIDATION TO CHECK FOR EMPTY FIELDS
    # Check for user name field is empty
        if username == "":
            t_message = "Login - empty field: Please fill in your user name."
            # Send user back to the dynamic html page (template), with a message
            return render_template("login.html", t_message = t_message)

        if password == "":
            t_message = "Login - empty field: Please fill in your password"
            return render_template("login.html", t_message = t_message)

        # Hash the password they entered into a encrypted hex string
    
    
    # Taking the time to build our SQL query string so that
    #   (a) we can easily and quickly read it; and
    #   (b) we can easily and quickly edit or add/remote lines.
    #   The more complex the query, the greater the benefits of this approach.
        s = ""
        s += "SELECT"
        s += " * "
        s += " FROM users"
        s += " WHERE"
        s += "("
        s += " username = '" + username + "'"
        S += " AND"
        s += " password = '" + password_candidate + "'"
        s += ")"
        # NOTE: the format above allows for a user to try to insert
        #   potentially damaging code, commonly known as "SQL injection".
        #   In another article (link below) we will show how to
        #   prevent that by using stored procedures.
        #   Here we left it as you see, so as to keep it as simple as possible.

        # Catch and display any possible errors
        #   while TRYing to commit the SQL script.
        cur.execute(s)
        try:
            data = cur.fetchone()
            password = data['password']
            sha256_crypt.verify(password_candidate, password)
            session['logged_in'] = True
            session['username'] = username

            flash('You are now logged in', 'success')
            return redirect(url_for('dashboard'))

        except psycopg2.Error as e:
            t_message = "Postgres Database error: " + e + "/n SQL: " + s
            return render_template("login.html")
        cur.close()

        # Clean up
        cur.close()
      
    return render_template("login.html")
    ## New code end


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

    uploaded_file = pd.read_sql_table('trialdata_tbl',conn)

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
