# friendship-ledger-payment

A Python-based application integrated with PostgreSQL database, SMTP email service, and optional payment UI module, built with secure environment-based configuration.

🚀 Features
🔐 Secure PostgreSQL connection using .env
🗄️ Connection pooling for better performance
📧 SMTP email notifications (OTP / alerts / mails)
💳 Payment UI integration (if applicable)
⚙️ Modular and scalable Python architecture
🔒 No hardcoded credentials (secure design)
🧰 Tech Stack
Python 3.x
PostgreSQL
psycopg2
python-dotenv
SMTP (Gmail / email service)
Streamlit / UI framework (optional)
📁 Project Structure
project/
│
├── db.py                  # PostgreSQL connection pool
├── app.py                 # Main application
├── smtp_service.py        # Email service logic
├── payment_ui.py          # Payment interface (optional)
├── requirements.txt       # Dependencies
├── .env                   # Environment variables (not pushed)
└── README.md
