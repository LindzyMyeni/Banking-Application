from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATA_FILE = 'users.json'


# Load user data from JSON file
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, 'r') as f:
               return json.load(f)
    except json.JSONDecodeError:
        return{}

# Save user data to JSON file
def save_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Data successfully saved: {data}")

    except Exception as e:
         print(f"Error saving data: {e}")


# Generate a random, unique 8-digit account number
def generate_account_number():
    return str(random.randint(10000000, 99999999))


@app.route('/')
def homepage():
    return render_template('homepage.html')


@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        username = request.form['username']
        phone = request.form['phone']
        id_number = request.form['id_number']
        password = request.form['password']

        # Validate inputs
        if not all([name, surname, username, phone, id_number, password]):
            flash('All fields are required.', 'error')
            return redirect(url_for('create_account'))

        if not phone.isdigit() or len(phone) != 10:
            flash('Phone number must be exactly 10 digits.', 'error')
            return redirect(url_for('create_account'))

        if not id_number.isdigit() or len(id_number) != 13:
            flash('ID number must be exactly 13 digits.', 'error')
            return redirect(url_for('create_account'))

        data = load_data()
        print("Hello Lindo")
        # Check for unique username and ID number
        for account, details in data.items():
            if details['id_number'] == id_number:
                flash('An account with this ID number already exists.', 'error')
                return redirect(url_for('create_account'))
            if details['username'] == username:
                flash('Username already exists. Please choose a different username.', 'error')
                return redirect(url_for('create_account'))

        # Generate unique account number
        while True:
            account_number = generate_account_number()
            if account_number not in data:
                break

        # Hash password and create account
        hashed_password = generate_password_hash(password)
        data[account_number] = {
            "name": name,
            "surname": surname,
            "username": username,
            "phone": phone,
            "id_number": id_number,
            "password": hashed_password,
            "balance": 0,
            "transactions": []
        }

        save_data(data)
        flash(f'Account created successfully! Your account number is {account_number}.', 'success')
        return redirect(url_for('login'))

    return render_template('create_account.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        data = load_data()

        for account, details in data.items():
            if details['username'] == username and check_password_hash(details['password'], password):
                session['account_number'] = account
                return redirect(url_for('dashboard'))

        flash('Invalid username or password. Please try again.', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'account_number' not in session:
        return redirect(url_for('login'))

    account_number = session['account_number']
    data = load_data()
    balance = data[account_number]['balance']
    return render_template('dashboard.html', balance=f"R{balance:.2f}", account_number=account_number)


@app.route('/deposit', methods=['POST'])
def deposit():
    if 'account_number' not in session:
        return redirect(url_for('login'))

    amount = request.form.get('amount', type=float)
    if amount <= 0:
        flash('Deposit amount must be greater than zero.', 'error')
        return redirect(url_for('dashboard'))

    account_number = session['account_number']
    data = load_data()

    data[account_number]['balance'] += amount
    data[account_number]['transactions'].append({
        "type": "Deposit",
        "amount": f"R{amount:.2f}",
        "to": account_number,
        "from": None,
        "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    save_data(data)

    flash('Deposit successful!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/withdraw', methods=['POST'])
def withdraw():
    if 'account_number' not in session:
        return redirect(url_for('login'))

    amount = request.form.get('amount', type=float)
    if amount <= 0:
        flash('Withdrawal amount must be greater than zero.', 'error')
        return redirect(url_for('dashboard'))

    account_number = session['account_number']
    data = load_data()

    if data[account_number]['balance'] >= amount:
        data[account_number]['balance'] -= amount
        data[account_number]['transactions'].append({
            "type": "Withdrawal",
            "amount": f"-R{amount:.2f}",
            "to": None,
            "from": account_number,
            "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        save_data(data)
        flash('Withdrawal successful!', 'success')
    else:
        flash('Insufficient balance.', 'error')

    return redirect(url_for('dashboard'))


@app.route('/transfer', methods=['POST'])
def transfer():
    if 'account_number' not in session:
        return redirect(url_for('login'))

    recipient_account = request.form['recipient']
    amount = request.form.get('amount', type=float)
    account_number = session['account_number']
    data = load_data()

    if amount <= 0:
        flash('Transfer amount must be greater than zero.', 'error')
    elif recipient_account == account_number:
        flash('You cannot transfer money to your own account.', 'error')
    elif recipient_account not in data:
        flash('Recipient account not found.', 'error')
    elif data[account_number]['balance'] < amount:
        flash('Insufficient balance.', 'error')
    else:
        data[account_number]['balance'] -= amount
        data[account_number]['transactions'].append({
            "type": "Transfer Out",
            "amount": f"-R{amount:.2f}",
            "to": recipient_account,
            "from": account_number,
            "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        data[recipient_account]['balance'] += amount
        data[recipient_account]['transactions'].append({
            "type": "Transfer In",
            "amount": f"R{amount:.2f}",
            "to": recipient_account,
            "from": account_number,
            "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        save_data(data)
        flash('Transfer successful!', 'success')

    return redirect(url_for('dashboard'))


@app.route('/transaction_history')
def transaction_history():
    if 'account_number' not in session:
        return redirect(url_for('login'))

    account_number = session['account_number']
    data = load_data()
    transactions = data[account_number]['transactions']

    return render_template('transaction_history.html', transactions=transactions)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('homepage'))


if __name__ == '__main__':
    app.run(debug=True)
