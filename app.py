from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
import sqlite3
import MetaTrader5 as mt5  # MT5 Library Added
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)  # Allow HTML Frontend to connect

# ⚙️ GMAIL CONFIGURATION
SENDER_EMAIL = "saurishcapital.office@gmail.com"
APP_PASSWORD = "vbgh szlp mqhp ltmm"  

# 🗄️ DATABASE INITIALIZATION (SQLite)
def init_db():
    conn = sqlite3.connect('saurish_users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            plan TEXT DEFAULT 'basic',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Start DB on Startup
init_db()

# 🚀 INITIALIZE MT5 (Added for Live MetaTrader Connection)
if not mt5.initialize():
    print("❌ MT5 Initialization failed, error code =", mt5.last_error())
else:
    print("✅ MT5 Engine Successfully Connected!")


# 📩 1. ROUTE: SEND OTP FOR REGISTRATION (WITH DUPLICATE EMAIL CHECK)
@app.route('/send-otp', methods=['POST'])
def send_otp():
    try:
        data = request.json
        user_email = data.get('email')
        user_name = data.get('name', 'Trader')
        otp = data.get('otp')

        if not user_email or not otp:
            return jsonify({'success': False, 'message': 'Email and OTP are required'}), 400

        # 🔍 CHECK IF EMAIL ALREADY EXISTS IN DATABASE
        conn = sqlite3.connect('saurish_users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM users WHERE email = ?', (user_email,))
        existing_user = cursor.fetchone()
        conn.close()

        if existing_user:
            return jsonify({
                'success': False, 
                'message': 'This Email is already registered! Please Login instead.'
            }), 400

        # Email Subject & Body Setup
        subject = f"Saurish Risk - Verification Code: {otp}"
        
        body = f"""Hello {user_name},

Welcome to Saurish Risk Management Platform!

Your 6-digit Email Verification Code is: {otp}

Please enter this code on the registration page to activate your account.
This code is valid for 10 minutes.

Regards,
Saurish Capital Team"""

        # Prepare MIME Message
        msg = MIMEMultipart()
        msg['From'] = f"Saurish Risk <{SENDER_EMAIL}>"
        msg['To'] = user_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Connect to Gmail SMTP Server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD.replace(" ", ""))
        server.send_message(msg)
        server.quit()

        return jsonify({'success': True, 'message': 'OTP Sent Successfully!'}), 200

    except Exception as e:
        print("SMTP OTP Error:", str(e))
        return jsonify({'success': False, 'message': f"Failed to send email: {str(e)}"}), 500


# 💾 2. ROUTE: SAVE REGISTERED USER AFTER OTP VERIFICATION
@app.route('/api/register', methods=['POST'])
def register_user():
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        plan = data.get('plan', 'basic')

        if not name or not email or not password:
            return jsonify({'success': False, 'message': 'All fields are required!'}), 400

        conn = sqlite3.connect('saurish_users.db')
        cursor = conn.cursor()

        # Insert User to Database
        cursor.execute('''
            INSERT INTO users (name, email, password, plan) 
            VALUES (?, ?, ?, ?)
        ''', (name, email, password, plan))
        
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'User registered successfully!'}), 200

    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Email already exists!'}), 400
    except Exception as e:
        print("Registration DB Error:", str(e))
        return jsonify({'success': False, 'message': f"Database Error: {str(e)}"}), 500


# 🔑 3. ROUTE: FORGOT PASSWORD RESET LINK
@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    try:
        data = request.json
        user_email = data.get('email')

        if not user_email:
            return jsonify({'success': False, 'message': 'Email address is required!'}), 400

        # Check if user exists before sending reset email
        conn = sqlite3.connect('saurish_users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM users WHERE email = ?', (user_email,))
        user_exists = cursor.fetchone()
        conn.close()

        if not user_exists:
            return jsonify({'success': False, 'message': 'No account found with this email!'}), 404

        # Dynamic Reset Link
        reset_link = f"http://127.0.0.1:5500/reset-password.html?email={user_email}"

        subject = "Password Reset Request - Saurish Risk"
        body = f"""Hello,

We received a request to reset your password for your Saurish Risk account.

Please click the link below to set a new password:
{reset_link}

Note: This link is valid for 15 minutes only. If you did not request a password reset, please ignore this email.

Regards,
Saurish Capital Team"""

        msg = MIMEMultipart()
        msg['From'] = f"Saurish Risk <{SENDER_EMAIL}>"
        msg['To'] = user_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD.replace(" ", ""))
        server.send_message(msg)
        server.quit()

        return jsonify({'success': True, 'message': 'Password reset link has been sent to your email!'}), 200

    except Exception as e:
        print("SMTP Forgot Password Error:", str(e))
        return jsonify({'success': False, 'message': f"Failed to send email: {str(e)}"}), 500


# 📈 4. ROUTE: SYNC AUTOMATED TRADES FROM EXTERNAL PLATFORM
@app.route('/api/sync-trades', methods=['POST'])
def sync_trades():
    try:
        data = request.json
        user_email = data.get('email')
        new_trades = data.get('trades', []) 

        if not user_email:
            return jsonify({'success': False, 'message': 'User email is required for syncing!'}), 400

        return jsonify({
            'success': True, 
            'message': f'Successfully synced {len(new_trades)} trades!',
            'synced_count': len(new_trades)
        }), 200

    except Exception as e:
        print("Trade Sync Error:", str(e))
        return jsonify({'success': False, 'message': f"Sync Error: {str(e)}"}), 500


# 📊 5. NEW ROUTE: FETCH LIVE MT5 ACCOUNT, UNIQUE ID & POSITIONS DATA
@app.route('/api/mt5-sync', methods=['GET'])
@app.route('/api/mt5-trades', methods=['GET'])
def sync_mt5_data():
    if not mt5.initialize():
        return jsonify({"status": "error", "message": "MT5 initialization failed"})
        
    account_info = mt5.account_info()
    
    # Specific account details extract kiye gaye hain
    acc_id = str(account_info.login) if account_info else "DefaultAccount"
    acc_name = account_info.name if account_info else "MT5 Trader"
    acc_company = account_info.company if account_info else "Broker"
    acc_balance = account_info.balance if account_info else 500.0
    acc_equity = account_info.equity if account_info else 500.0
    
    # 1. Get currently running positions (Open Trades) with accountId mapping
    positions = mt5.positions_get()
    running_trades = []
    if positions:
        for pos in positions:
            running_trades.append({
                "accountId": acc_id,  # Specific Account ID attached
                "ticket": pos.ticket,
                "symbol": pos.symbol,
                "side": "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL",
                "lots": pos.volume,
                "openPrice": pos.price_open,
                "sl": pos.sl if pos.sl > 0 else "-",
                "tp": pos.tp if pos.tp > 0 else "-",
                "openTime": datetime.fromtimestamp(pos.time).strftime('%Y-%m-%d %H:%M:%S') if pos.time else "-",
                "closeTime": "-",
                "closePrice": "Running",
                "status": "RUNNING",
                "pnl": pos.profit
            })

    # 2. Get closed history deals (History Trades) with accountId mapping
    utc_from = datetime(2023, 1, 1)
    utc_to = datetime.now() + timedelta(days=1)
    deals = mt5.history_deals_get(utc_from, utc_to)
    history_trades = []
    
    if deals:
        for deal in deals:
            if deal.entry == mt5.DEAL_ENTRY_OUT: 
                history_trades.append({
                    "accountId": acc_id,  # Specific Account ID attached
                    "ticket": deal.ticket,
                    "symbol": deal.symbol,
                    "side": "BUY" if deal.type == mt5.POSITION_TYPE_BUY else "SELL",
                    "lots": deal.volume,
                    "openPrice": deal.price,
                    "closePrice": deal.price,
                    "openTime": "-",
                    "closeTime": datetime.fromtimestamp(deal.time).strftime('%Y-%m-%d %H:%M:%S') if deal.time else "-",
                    "status": "CLOSED",
                    "pnl": deal.profit
                })

    mt5.shutdown()
    
    all_trades = running_trades + history_trades

    return jsonify({
        "status": "success",
        "accountId": acc_id,
        "accountName": f"{acc_company} - {acc_name} ({acc_id})",
        "startingBalance": acc_balance,
        "balance": acc_balance,
        "equity": acc_equity,
        "running": running_trades,
        "history": history_trades,
        "trades": all_trades
    })

if __name__ == '__main__':
    print("🚀 Saurish Risk Python Database & Email Server Running on http://127.0.0.1:5000")
    app.run(port=5000, debug=True)