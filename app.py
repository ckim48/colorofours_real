from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify
import sqlite3
import os
from werkzeug.utils import secure_filename
from changeImg import changeImage
from datetime import datetime
import pytesseract
from PIL import Image
import re
import random
import string

app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'static/processed'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(PROCESSED_FOLDER):
    os.makedirs(PROCESSED_FOLDER)

# Ensure the directories for processed images exist
processed_dirs = ['static/images/normal', 'static/images/protanopia', 'static/images/deuteranopia', 'static/images/tritanopia']
for directory in processed_dirs:
    if not os.path.exists(directory):
        os.makedirs(directory)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

def isAdmin():
    if session.get('user',0) == "testtest":
        return True
    return False

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def generate_unique_filename(filename, username):
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    name, ext = os.path.splitext(filename)
    unique_filename = f"{name}_{username}_{token}{ext}"
    return unique_filename

@app.route('/shop')
def shop():
    isLogin = False
    if 'user' in session:
        isLogin = True
        page = request.args.get('page', 1, type=int)
        per_page = 4
        offset = (page - 1) * per_page

        conn = get_db_connection()
        images = conn.execute('SELECT * FROM images WHERE status = "accepted" ORDER BY upload_date DESC LIMIT ? OFFSET ?',
                              (per_page, offset)).fetchall()
        total_images = conn.execute('SELECT COUNT(*) FROM images WHERE status = "accepted"').fetchone()[0]
        conn.close()

        total_pages = (total_images + per_page - 1) // per_page

        return render_template('shop.html', isLogin=isLogin, images=images, page=page, total_pages=total_pages)
    return render_template('login.html', isLogin=isLogin)


@app.route('/')
def index():
    isLogin = False
    if 'user' in session:
        isLogin = True
    Admin = False
    if isAdmin():
        Admin = True
    return render_template('index.html', isLogin=isLogin, Admin=Admin)

@app.route('/about')
def about():
    isLogin = False
    if 'user' in session:
        isLogin = True
    return render_template('overview.html', isLogin=isLogin)

@app.route('/logout')
def logout():
    session.clear()
    return render_template('index.html', isLogin=False)

@app.route('/upload')
def upload():
    isLogin = False
    if 'user' not in session:
        isLogin = False
    else:
        isLogin = True
    return render_template('upload.html',isLogin = isLogin)

@app.route('/donate')
def donate():
    isLogin = False
    if 'user' not in session:
        isLogin = False
    else:
        isLogin = True
    return render_template('Donate.html', isLogin = isLogin)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        isLogin = False
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users where username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        if user:
            session["user"] = user["username"]
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password", 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        repassword = request.form['repassword']
        fullname = request.form['fullname']
        email = request.form['email']
        phone = request.form['phone']

        if password != repassword:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))

        conn = get_db_connection()
        user_exists = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user_exists:
            flash('Username already exists', 'danger')
            conn.close()
            return redirect(url_for('register'))

        conn.execute('INSERT INTO users (username, password, name, email, phone) VALUES (?, ?, ?, ?, ?)',
                     (username, password, fullname, email, phone))
        conn.commit()
        conn.close()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/preview', methods=['POST'])
def preview():
    image = request.files['image']

    if image:
        filename = secure_filename(image.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(filepath)

        changeImage(filepath, session["user"], filename)

        user = session["user"]
        original_image = url_for('static', filename=f'images/normal/{user}_n_{filename}')
        prot_image = url_for('static', filename=f'images/protanopia/{user}_p_{filename}')
        deut_image = url_for('static', filename=f'images/deuteranopia/{user}_d_{filename}')
        trit_image = url_for('static', filename=f'images/tritanopia/{user}_t_{filename}')

        response = {
            'originalImage': original_image,
            'protImage': prot_image,
            'deutImage': deut_image,
            'tritImage': trit_image
        }

        return jsonify(response)
    else:
        return jsonify({'error': 'Please upload an image.'}), 400

@app.route('/upload_image', methods=['POST'])
def upload_image():
    title = request.form['title']
    description = request.form['description']
    image = request.files['image']
    username = session["user"] if "user" in session else "test"  # Use session to get the username
    upload_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if image and title and description:
        filename = secure_filename(image.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(filepath)

        changeImage(filepath, username, filename)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO images (title, description, filepath, username, upload_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, description, filepath, username, upload_date, 'pending'))
        conn.commit()
        conn.close()

        return jsonify({'message': 'Image uploaded successfully!'})
    else:
        return jsonify({'error': 'Please fill out all fields and upload an image.'}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/processed/<filename>')
def processed_file(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename)

@app.route('/orimg/<filename>')
def orimg(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/admin')
def admin():
    isLogin = False
    if 'user' in session:
        isLogin = True
    conn = get_db_connection()
    images = conn.execute('SELECT * FROM images WHERE status = "pending"').fetchall()
    receipts = conn.execute('SELECT * FROM receipts WHERE status = "pending"').fetchall()

    customers = conn.execute('SELECT * FROM receipts WHERE status = "accepted"').fetchall()
    conn.close()
    return render_template('admin.html', images=images, receipts=receipts, isLogin = isLogin, customers=customers)



@app.route('/myprofile')
def myprofile():
    isLogin = False

    if 'user' not in session:
        return redirect(url_for('login'))
    else:
        isLogin = True

    username = session['user']
    conn = get_db_connection()

    user = conn.execute('SELECT Username, Name, Email, Phone FROM Users WHERE Username = ?', (username,)).fetchone()

    receipts = conn.execute('Select * From receipts WHERE username =?', (username,)).fetchall()

    paintings = conn.execute('Select * From images WHERE username =?', (username,)).fetchall()
    conn.close()
    return render_template('myprofile.html', receipts=receipts, images=paintings, user=user, isLogin = isLogin)



@app.route('/accept/<int:image_id>')
def accept(image_id):
    conn = get_db_connection()
    conn.execute('UPDATE images SET status = ? WHERE id = ?', ('accepted', image_id))
    conn.commit()
    conn.close()
    flash('Image accepted successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/reject/<int:image_id>')
def reject(image_id):
    conn = get_db_connection()
    conn.execute('UPDATE images SET status = ? WHERE id = ?', ('rejected', image_id))
    conn.commit()
    conn.close()
    flash('Image rejected successfully!', 'danger')
    return redirect(url_for('admin'))

@app.route('/preview_receipt', methods=['POST'])
def preview_receipt():
    image = request.files['receipt']

    if image:
        filename = secure_filename(image.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(filepath)

        text = pytesseract.image_to_string(Image.open(filepath))

        # Extract name and price
        name, price = extract_name_and_price(text)

        return jsonify({'name': name, 'price': price})
    else:
        return jsonify({'error': 'Please upload an image.'}), 400

@app.route('/upload_receipt', methods=['GET', 'POST'])
def upload_receipt():
    if request.method == 'POST':
        if 'user' not in session:
            return redirect(url_for('login'))

        image = request.files['receipt']
        if image:
            filename = secure_filename(image.filename)
            username = session['user']
            unique_filename = generate_unique_filename(filename, username)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            image.save(filepath)

            text = pytesseract.image_to_string(Image.open(filepath))

            # Extract name and price
            name, price = extract_name_and_price(text)

            # Save to database
            conn = get_db_connection()
            conn.execute('INSERT INTO receipts (username, name, price, filepath, status) VALUES (?, ?, ?, ?, ?)',
                         (username, name, price, filepath, 'pending'))
            conn.commit()
            conn.close()

            return jsonify({'name': name, 'price': price, 'filepath': filepath})
        else:
            return jsonify({'error': 'No file uploaded'}), 400
    else:
        if 'user' not in session:
            return redirect(url_for('login'))
        return render_template('upload_receipt.html')

def extract_name_and_price(text):
    lines = text.split('\n')
    name = None
    price = None

    # Regex to find price and name
    price_pattern = re.compile(r'\$\d+\.\d{2}')
    name_pattern = re.compile(r'^[A-Za-z ]+$')

    for line in lines:
        price_match = price_pattern.search(line)
        name_match = name_pattern.match(line.strip())

        if price_match:
            price = price_match.group()

        if name_match:
            name = name_match.group()

        if name and price:
            break

    return name, price

@app.route('/fetch_receipts')
def fetch_receipts():
    conn = get_db_connection()
    receipts = conn.execute('SELECT * FROM receipts WHERE status = "pending"').fetchall()
    conn.close()
    return jsonify({'receipts': [dict(receipt) for receipt in receipts]})

@app.route('/accept_receipt/<int:receipt_id>')
def accept_receipt(receipt_id):
    conn = get_db_connection()
    conn.execute('UPDATE receipts SET status = ? WHERE id = ?', ('accepted', receipt_id))
    conn.commit()
    conn.close()
    flash('Receipt accepted successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/reject_receipt/<int:receipt_id>')
def reject_receipt(receipt_id):
    conn = get_db_connection()
    conn.execute('UPDATE receipts SET status = ? WHERE id = ?', ('rejected', receipt_id))
    conn.commit()
    conn.close()
    flash('Receipt rejected successfully!', 'danger')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True, port=8000)
