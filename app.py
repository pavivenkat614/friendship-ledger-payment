import streamlit as st
import pandas as pd
import random
import os
import urllib.parse
import qrcode
from io import BytesIO
import smtplib
from pathlib import Path

from dotenv import load_dotenv
from db import *


import os
from dotenv import load_dotenv

load_dotenv()

print("HOST:", os.getenv("DB_HOST"))
print("DB:", os.getenv("DB_NAME"))
print("USER:", os.getenv("DB_USER"))
print("PORT:", os.getenv("DB_PORT"))
# ---------------- ENV ----------------
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Friendship Ledger", layout="wide")

# ---------------- SESSION ----------------
for k in ["user_id", "username", "group_id", "otp", "otp_sent"]:
    if k not in st.session_state:
        st.session_state[k] = None

# ---------------- OTP ----------------
def send_otp(email):
    otp = str(random.randint(100000, 999999))

    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")

    msg = f"Subject: OTP\n\nYour OTP is {otp}"

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(sender, password)
            s.sendmail(sender, email, msg)

        st.session_state.otp = otp
        return True
    except Exception as e:
        st.error(e)
        return False

# ---------------- UPI ----------------
def generate_upi(amount, upi_id, name):
    params = {
        "pa": upi_id,
        "pn": name,
        "am": f"{float(amount):.2f}",
        "cu": "INR",
        "tn": "Split"
    }
    return "upi://pay?" + urllib.parse.urlencode(params)

def generate_qr(link):
    img = qrcode.make(link)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ---------------- LOGIN ----------------
def login_ui():
    st.title("💰 Friendship Ledger")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        u = st.text_input("Username/Email")
        p = st.text_input("Password", type="password")

        if st.button("Login"):
            uid = login_user(u, p)
            if uid:
                st.session_state.user_id = uid
                st.session_state.username = u
                st.rerun()
            else:
                st.error("Invalid login")

    with tab2:
        u = st.text_input("Username", key="r1")
        e = st.text_input("Email", key="r2")
        p = st.text_input("Password", type="password", key="r3")

        if st.button("Send OTP"):
            if send_otp(e):
                st.session_state.otp_sent = True

        if st.session_state.otp_sent:
            otp_in = st.text_input("Enter OTP")

            if st.button("Register"):
                if otp_in == st.session_state.otp:
                    if register_user(u, e, p):
                        st.success("Registered")
                    else:
                        st.error("User exists")

# ---------------- MAIN ----------------
if st.session_state.user_id is None:
    login_ui()
    st.stop()

st.sidebar.success(f"👤 {st.session_state.username}")

if st.sidebar.button("Logout"):
    st.session_state.user_id = None
    st.rerun()

st.title("📊 Dashboard")

# ---------------- GROUP ----------------
groups = get_user_groups(st.session_state.user_id)

if groups.empty:
    st.warning("Create group first")
    st.stop()

group_name = st.selectbox("Select Group", groups["name"])
gid = int(groups[groups["name"] == group_name]["id"].values[0])
st.session_state.group_id = gid

# ---------------- FRIENDS ----------------
st.subheader("👥 Friends")

name = st.text_input("Name")
upi = st.text_input("UPI ID")

if st.button("Add Friend"):
    add_friend(st.session_state.user_id, gid, name, upi)
    st.rerun()

friends = get_friends(st.session_state.user_id, gid)

# ---------------- EXPENSE ----------------
st.subheader("💸 Add Expense")

desc = st.text_input("Description")
amt = st.number_input("Amount", min_value=0.0)

payer = st.selectbox(
    "Paid By",
    friends["id"],
    format_func=lambda x: friends[friends["id"] == x]["name"].values[0]
)

split = st.multiselect(
    "Split Among",
    friends["id"],
    default=list(friends["id"])
)

if st.button("Add Expense"):
    add_expense(
        st.session_state.user_id,
        gid,
        "2026-01-01",
        desc,
        int(payer),
        float(amt),
        split
    )
    st.rerun()

# ---------------- LOAD EXPENSES ----------------
df = get_expenses(st.session_state.user_id, gid)
st.subheader("📋 Expenses")
st.dataframe(df, use_container_width=True)

# ---------------- BALANCE ----------------
def calc_balance(df, friends):
    bal = {n: 0 for n in friends["name"]}

    for _, r in df.iterrows():
        if not r["splits"]:
            continue

        parts = r["splits"].split(",")
        share = r["amount"] / len(parts)

        for p in parts:
            bal[p] -= share

        bal[r["paid_by"]] += r["amount"]

    return bal

if not df.empty:
    bal = calc_balance(df, friends)

    st.subheader("💡 Balance")

    for k, v in bal.items():
        if v > 0:
            st.success(f"{k} gets ₹{v:.0f}")
        else:
            st.error(f"{k} owes ₹{-v:.0f}")

# ---------------- PAYMENT ----------------
st.subheader("💳 Payments")

payments = get_payments(gid)

for _, p in payments.iterrows():
    st.write(f"{p['payer']} → {p['receiver']} : ₹{p['amount']}")

    if p["status"] == "PAID":
        st.success("Paid")
    else:
        link = generate_upi(p["amount"], "dummy@upi", p["receiver"])

        st.link_button("Pay Now", link)

        if st.button("Mark Paid", key=p["id"]):
            mark_payment_paid(p["id"])
            st.rerun()