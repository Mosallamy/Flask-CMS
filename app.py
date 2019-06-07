import datetime
import os
from flask import Flask, render_template, flash,redirect,url_for,session,logging,request,abort,wrappers
from wtforms import Form,StringField,TextAreaField,PasswordField,validators,RadioField,FileField
from passlib.hash import sha256_crypt
from flaskext.mysql import MySQL
from flaskext import mysql
from pymysql.cursors import DictCursor
from functools import wraps
#from flask_mysqldb import MySQL
from flask_sqlalchemy import SQLAlchemy
from string import Template
import re
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = '/Users/Mosallamy/Desktop/myFlaskApp/app/static'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['MYSQL_DATABASE_HOST'] = 'localhost'
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'myflaskapp'

mysql = MySQL(app,cursorclass=DictCursor)

def is_logged_in(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if 'logged_in' in session:
            return f(*args,**kwargs)
        else:
            flash('Unauthorized, Please login','danger')
            return redirect(url_for('login'))
    return wrap

def is_admin(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if 'logged_in' in session and (session['role'] == 'admin'):
            return f(*args,**kwargs)
        else:
            return redirect(url_for('dashboard'))
    return wrap

def is_super(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if 'logged_in' in session and (session['role'] == 'super'):
            return f(*args,**kwargs)
        else:
            return redirect(url_for('dashboard'))
    return wrap

def logged_out(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if 'logged_in' not in session:
            return f(*args,**kwargs)
        else:
            return redirect(url_for('index'))
    return wrap

#----------------------------------------------   index page   ----------------------------------------------#

@app.route('/')
def index():
    return render_template('index.html', title ='Home')

#----------------------------------------------   About page   ----------------------------------------------#

@app.route('/about/')
def about():
    return render_template('about.html', title ='About')

#----------------------------------------------   Articles page   ----------------------------------------------#

@app.route('/articles/')
def articles():

    connection = mysql.connect()
    cursor = connection.cursor()
    result = cursor.execute('select * from article')
    article = cursor.fetchall()
    connection = mysql.connect()



    if result > 0:
        return render_template('articles.html', article=article, title ='Articles')
    else:
        msg = 'No Articles Found'
        return render_template('articles.html', msg=msg, title ='Articles')

    cursor.close()



#----------------------------------------------   Single Article page   ----------------------------------------------#

@app.route('/article/<int:id>/')
def article(id):

    connection = mysql.connect()
    cursor = connection.cursor()
    result = cursor.execute('select * from article where id = %s',[id])
    article = cursor.fetchone()
    result = cursor.execute('select username from users where id = %s', article['author'])
    name = cursor.fetchone()
    result = cursor.execute('select id from article where id > %s order by id ASC',id)
    last = cursor.fetchone()
    if last: last = last['id']
    if(id != last and last != None):
        last = last
    else:
        last = id
    result = cursor.execute('select id from article where id < %s order by id desc',id)
    first = cursor.fetchone()

    if first: first = first['id']

    if (id != first and first != None):
        first = first
    else:
        first = id
    cursor.close()
    return render_template('article.html', id=id, article=article, name=name['username'],first=first,last=last)

#----------------------------------------------   Register Page   ----------------------------------------------#

class RegisterForm(Form):

    name = StringField("Name",[validators.Length(min=1,max=30)] )
    username = StringField("Username",[validators.Length(min=4,max=25)] )
    email = StringField("Email",[validators.Length(min=6,max=50)] )
    password = PasswordField("Password",[
        validators.DataRequired(),
        validators.EqualTo('confirm',message="password does not match")

    ])
    confirm = PasswordField("Confirm Password")
    example = RadioField('Label',[validators.DataRequired()] ,choices=[('value', 'description'), ('value_two', 'whatever'),('value_two', 'whatever')])


@app.route('/regsiter/',methods=['GET','POST'])
@logged_out
def regsiter():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        connection = mysql.connect()
        cursor = connection.cursor()
        check = cursor.execute('select * from users where username = %s and email = %s', (username,email))

        cursor.execute('INSERT INTO users (name,email,username,password) VALUES (%s,%s,%s,%s)',(name,email,username,password))
        connection.commit()
        cursor.close()

        flash('You are now registered and can login','success')

        return redirect(url_for('login'))
    return render_template('regsiter.html', form=form)

#----------------------------------------------   Login Page   ----------------------------------------------#

@app.route('/login/',methods=['GET','POST'])
@logged_out
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate= request.form['password']
        cursor = mysql.connect().cursor()
        result  = cursor.execute('select * from users where username = %s',(username))

        if result > 0:
            data = cursor.fetchone()
            password  = data['password']

            if sha256_crypt.verify(password_candidate,password):
                connection = mysql.connect()
                cursor = connection.cursor()
                cursor.execute("SELECT COUNT(*) FROM article")
                property_count = cursor.fetchone()
                cursor.execute("SELECT role FROM users where id = %s",data['id'])
                role = cursor.fetchone()
                session['count'] = property_count['COUNT(*)']
                session['role'] = role['role']
                session['logged_in'] = True
                session['username'] = username
                session['id'] = data['id']
                flash('You are noew logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'invalid username or password'
                return render_template('login.html', error=error)
            cursor.close()
        else:
            error = 'invalid username or password'
            return render_template('login.html', error=error)

    return render_template('login.html')





#----------------------------------------------   Logout Page   ----------------------------------------------#

@app.route('/logout/')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out','success')
    return redirect(url_for('login'))

#----------------------------------------------   Dashboard Page   ----------------------------------------------#

@app.route('/dashboard/')
@is_logged_in
def dashboard():
    connection = mysql.connect()
    cursor = connection.cursor()
    username = session['username']
    result = cursor.execute('select id from users where username = %s',username)
    id = cursor.fetchone()

    if session['role'] == 'admin':
        result = cursor.execute('select * from article')
        article = cursor.fetchall()
    else:
        result = cursor.execute('select * from article where author = %s', id['id'])
        article = cursor.fetchall()

    if result > 0:
        return render_template('dashboard.html', article=article, username=username, result=result)
    else:
        msg = 'No Articles Found'
        return render_template('dashboard.html', msg=msg, result=result)

    cursor.close()

    return render_template('/dashboard.html')

#----------------------------------------------   Add article Page   ----------------------------------------------#

class ArticleForm(Form):
    title = StringField("Title",[validators.Length(min=1,max=200)] )
    body = TextAreaField("Body",[validators.Length(min=1)])
    file = FileField()

@app.route('/add_article/',methods=['GET','POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data
        username = session['username']
        if request.files['file']:
            file = request.files['file']
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = None
        connection = mysql.connect()
        cursor = connection.cursor()

        result = cursor.execute(' SELECT id FROM users WHERE username = %s', (username))
        id = cursor.fetchone()
        result = cursor.execute('insert into article(title,body,author,photo) values (%s,%s,%s,%s)',(title,body,id['id'],filename))

        cursor.execute("SELECT COUNT(*) FROM article")
        property_count = cursor.fetchone()
        session['count'] = property_count['COUNT(*)']
        connection.commit()
        cursor.close()

        flash('Article Created', 'success')

        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)

#----------------------------------------------   Edit article Page   ----------------------------------------------#

@app.route('/edit_article/<string:id>/',methods=['GET','POST'])
@is_logged_in
def edit_article(id):
    connection = mysql.connect()
    cursor = connection.cursor()

    result = cursor.execute('SELECT * from article where id = %s',[id])

    article = cursor.fetchone()

    form = ArticleForm(request.form)

    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        connection = mysql.connect()
        cursor = connection.cursor()
        result = cursor.execute('update article set title = %s,body=%s where id = %s',(title,body,id))

        connection.commit()
        cursor.close()

        flash('Article Updated', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)

#----------------------------------------------   Delete article Page   ----------------------------------------------#

@app.route('/delete_article/<string:id>/',methods=['post'])
@is_logged_in
def delete_article(id):
    connection = mysql.connect()
    cursor = connection.cursor()
    result = cursor.execute('select photo from article where id = %s', [id])
    photo = cursor.fetchone()
    print (photo)
    if photo['photo']:
        print photo
        photo = photo['photo']
        os.remove(os.path.join(UPLOAD_FOLDER, photo))
    result = cursor.execute('delete from article where id = %s', [id])
    cursor.execute("SELECT COUNT(*) FROM article")
    property_count = cursor.fetchone()
    session['count'] = property_count['COUNT(*)']
    connection.commit()
    cursor.close()
    flash('Article Deleted', 'success')

    return redirect(url_for('dashboard'))

#----------------------------------------------   Users Page   ----------------------------------------------#
@app.route('/users/')
@is_super
def users():
    connection = mysql.connect()
    cursor = connection.cursor()
    result = cursor.execute('select * from users where id != %s ',(session['id']))
    user = cursor.fetchall()
    cursor.close()

    return render_template('users.html', user=user)

#----------------------------------------------   Delete user Page   ----------------------------------------------#

@app.route('/delete_user/<string:id>/',methods=['post'])
@is_super
def delete_user(id):
    connection = mysql.connect()
    cursor = connection.cursor()

    result = cursor.execute('delete from users where id = %s', [id])

    connection.commit()
    cursor.close()
    flash('User Deleted', 'success')

    return redirect(url_for('users'))

#----------------------------------------------   Update user Page   ----------------------------------------------#
class UpdateForm(Form):
    name = StringField("Name",[validators.Length(min=1,max=30)] )
    username = StringField("Username",[validators.Length(min=4,max=25)] )
    email = StringField("Email",[validators.Length(min=6,max=50)] )
    password = PasswordField("Password",[
        validators.DataRequired(),
        validators.EqualTo('confirm',message="password does not match")

    ])
    confirm = PasswordField("Confirm Password")

@app.route('/settings/',methods=['post','get'])
@is_logged_in
def settings():

    form = UpdateForm(request.form)

    connection = mysql.connect()
    cursor = connection.cursor()
    username = session['username']
    result = cursor.execute('SELECT * from users where username = %s',username)
    article = cursor.fetchone()

    id = article['id']
    form = UpdateForm(request.form)

    form.name.data = article['name']
    form.username.data = article['username']
    form.email.data = article['email']
    form.password.data = article['password']
    form.confirm.data = article['password']


    if request.method == 'POST' and form.validate():
        name = request.form['name']
        email = request.form['email']
        username = request.form['username']
        password = sha256_crypt.encrypt(str(request.form['password']))
        session['username'] = username
        connection = mysql.connect()
        cursor = connection.cursor()
        result = cursor.execute('update users set name = %s,email=%s,username=%s,password=%s where id = %s',(name,email,username,password,id))

        connection.commit()
        cursor.close()

        flash('User Updated', 'success')

        return redirect(url_for('dashboard'))
    
    return render_template('setting.html', form=form)

#----------------------------------------------   Update user Page   ----------------------------------------------#

@app.route('/update_user/<string:id>/',methods=['post'])
@is_logged_in
def update_user():
    return render_template('edit_user.html')
#----------------------------------------------   Author Page   ----------------------------------------------#
@app.route('/author/<name>/')
def author(name):
    connection = mysql.connect()
    cursor = connection.cursor()
    result  = cursor.execute('select id from users where username = %s ',name)

    if result > 0:
        id = cursor.fetchone()
        result = cursor.execute('select * from article where author = %s ', id['id'])
        article = cursor.fetchall()
        cursor.close()
        return render_template('author.html', article=article, name=name)
    else:
        msg = 'author not found'
        cursor.close()
        return render_template('author.html', msg=msg)

#----------------------------------------------   Authors Page   ----------------------------------------------#
@app.route('/authors/')
def authors():
    connection = mysql.connect()
    cursor = connection.cursor()
    result = cursor.execute('select * from users')
    authors = cursor.fetchall()
    cursor.close()
    return render_template('authors.html', authors=authors)
#----------------------------------------------   Assing admin   ----------------------------------------------#
@app.route('/assign_admin/<id>/',methods=['post'])
@is_super
def assign_admin(id):
    connection = mysql.connect()
    cursor = connection.cursor()
    result = cursor.execute('update users set role = "admin" where id = %s',id)
    connection.commit()
    cursor.close()
    #flash('User Assigned amdmin', 'success')
    return redirect(url_for('users'))
#----------------------------------------------   Assing user   ----------------------------------------------#
@app.route('/assign_user/<id>/',methods=['post'])
@is_super
def assign_user(id):
    connection = mysql.connect()
    cursor = connection.cursor()
    result = cursor.execute('update users set role = "user" where id = %s',id)
    connection.commit()
    cursor.close()
    #flash('User Assigned amdmin', 'success')
    return redirect(url_for('users'))

#----------------------------------------------   Feb Page   ----------------------------------------------#

@app.route('/feb')
def feb():
    x = []
    f1 = 0
    f2 = 1
    x.append(f1)

    for i in range (1,450):
        sum =f2+ f1;
        f1 = f2;
        f2 = sum
        x.append(f1)

    return render_template('feb.html', title='Feb', x=x)

#----------------------------------------------   Mosallamy   ----------------------------------------------#
@app.route('/mosallamy/',methods=['get'])
def ss(id=None):
    google_place_id = request.args.get('id', None)
    google_place_name = request.args.get('name', None)
    test = request.args.get('test')
    print(google_place_id)
    print(google_place_name)
    print(test)
    return render_template('mosallamy.html')

@app.route('/test/')
def test():
    return render_template('test.html')


if __name__ == '__main__':
    app.run(debug=True, port=2002)
