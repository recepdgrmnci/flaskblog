from flask import Flask
from flask import render_template
from flask import flash
from flask import redirect
from flask import url_for
from flask import session
from flask import logging
from flask import request
from flask_mysqldb import MySQL
from wtforms import Form
from wtforms import StringField
from wtforms import TextAreaField
from wtforms import PasswordField
from wtforms import validators
from passlib.hash import sha256_crypt
from functools import wraps

# Kullanıcı Giriş Decorator

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın","danger")
            return redirect(url_for("login"))
    return decorated_function

# Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.Length(min = 4, max = 25, message="İsim soyisim 4 ile 25 karakter arası uzunlukta olmalı")])
    username = StringField("Kullanıcı Adı",validators=[validators.Length(min = 4, max = 35, message="Kullanıcı adı 4 ile 25 karakter arası uzunlukta olmalı")])
    email = StringField("Email Adresi",validators=[validators.Email(message="Lütfen geçerli bir email adresi giriniz.")])
    password = PasswordField("Parola: ", validators=[
        validators.DataRequired(message="Lütfen bir parola belirleyin."),
        validators.EqualTo(fieldname = "confirm", message="Parolanız uyuşmuyor.")
    ])
    confirm = PasswordField("Parola Doğrula", validators=[
        validators.DataRequired(message="Bu alanı boş bırakamazsınız."),
        validators.EqualTo(fieldname = "password", message="Parolanız uyuşmuyor.")
    ])

class LoginForm(Form):
    username = StringField("Kullanıcı adı: ")
    password = PasswordField("Şifre: ")

app = Flask(__name__)
app.secret_key = "ybblog"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "ybblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

# Makale Sayfası
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles"
    result = cursor.execute(sorgu)
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)
    else:
        return render_template("articles.html")

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s"
    result = cursor.execute(sorgu,(session["username"],))
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)
    else:
        return render_template("dashboard.html")

#Kayıt Olma
@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO users(name,email,username,password) VALUES(%s,%s,%s,%s)"
        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarıyla kayıt yapıldı..","success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html",form=form)

# Login işlemi
@app.route("/login", methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST" and form.validate():
        username = form.username.data
        password_entered = form.password.data
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM users where username = %s"
        result = cursor.execute(sorgu,(username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Başarıyla giriş yapıldı","success")
                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Hatalı parola girdiniz","danger")
                return redirect(url_for("login"))
        else:
            flash("Kullanıcı adı kayıtlı değil","danger")
            return redirect(url_for("login"))
    else:
        return render_template("login.html",form = form)

# Makale Detay Sayfası
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE id = %s"
    result = cursor.execute(sorgu,(id,))
    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
        return render_template("article.html")

# Logout işlemi
@app.route("/logout")
def logout():
    session.clear()
    flash("Başarıyla çıkış yapıldı","success")
    return redirect(url_for("index"))

@app.route("/addarticle", methods = ["GET","POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO articles(title, author, content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale başarıyla eklendi..","success")
        redirect(url_for("dashboard"))
    return render_template("addarticle.html", form = form)

# Makale Silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM ARTICLES WHERE author = %s and id = %s"
    result = cursor.execute(sorgu,(session["username"],id))
    if result > 0:
        sorgu2 = "DELETE FROM ARTICLES WHERE author = %s and id = %s"
        result2 = cursor.execute(sorgu2,(session["username"],id))
        mysql.connection.commit()
        flash("Makale başarıyla silindi..","success")
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale bulunmuyor yada bu işleme yetkiniz bulunmuyor","danger")
        return redirect(url_for("index"))

# Makale Güncelleme
@app.route("/edit/<string:id>", methods = ["GET","POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE author = %s and id = %s"
        result = cursor.execute(sorgu,(session["username"],id))
        if result == 0:
            flash("Böyle bir makale bulunmuyor yada bu makeleyi güncellemeye yetkiniz bulunmuyor.","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html", form = form)
    else:
        # POST REQUEST
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data
        cursor = mysql.connection.cursor()
        sorgu2 = "UPDATE articles SET title = %s, content = %s WHERE id = %s and author = %s"
        cursor.execute(sorgu2,(newTitle,newContent,id,session["username"]))
        mysql.connection.commit()
        flash("Makale başarıyla güncellendi...","success")
        return redirect(url_for("dashboard"))

# Makale Form
class ArticleForm(Form):
    title = StringField("Makale Başlığı", validators=[
        validators.Length(min = 5, max = 100, message="Başlık alanı 5-100 karakter aralığında olmalıdır.")
    ])
    content = TextAreaField("Makale İçeriği", validators=[
        validators.Length(min = 10, message="İçerik 10 karakterden az olamaz.")
    ])

# Arama URL
@app.route("/search", methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE title like '%"+ keyword +"%' or content like '%"+ keyword +"%'"
        result = cursor.execute(sorgu)
        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadi.","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html", articles = articles)
if __name__ == "__main__":
    app.run(debug=True)