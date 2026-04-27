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
from datetime import datetime
from db import *

# ---------------- ENV ----------------
load_dotenv()
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

print("HOST:", os.getenv("DB_HOST"))
print("DB:", os.getenv("DB_NAME"))
print("USER:", os.getenv("DB_USER"))
print("PORT:", os.getenv("DB_PORT"))

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Friendship Ledger", layout="wide")

# ---------------- SESSION ----------------
for k in ["user_id", "username", "group_id", "otp", "otp_sent"]:
    if k not in st.session_state:
        st.session_state[k] = None


# ---------------- OTP ----------------
def get_otp_delivery_mode():
    return os.getenv("OTP_DELIVERY_MODE", "email").strip().lower()


def send_otp(email):
    otp = str(random.randint(100000, 999999))
    otp_delivery_mode = get_otp_delivery_mode()

    st.session_state.otp = otp

    if otp_delivery_mode == "debug":
        st.info(f"Debug OTP for testing: {otp}")
        return True

    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")

    if not sender or not password:
        st.error("Email configuration not set. Check your .env file.")
        return False

    msg = f"Subject: OTP\n\nYour OTP is {otp}"

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as s:
            s.starttls()
            s.login(sender, password)
            s.sendmail(sender, email, msg)

        return True

    except Exception as e:
        st.error(f"Failed to send OTP: {str(e)}")
        st.info("If your network blocks SMTP, set OTP_DELIVERY_MODE=debug in .env and try again.")
        return False


# ---------------- UPI ----------------
def generate_upi(amount, upi_id, name):
    params = {
        "pa": upi_id,
        "pn": name,
        "am": f"{float(amount):.2f}",
        "cu": "INR",
        "tn": "Split",
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

        if get_otp_delivery_mode() == "debug":
            st.caption("OTP debug mode is enabled. The generated OTP will be shown in the app.")

        if st.button("Send OTP"):
            if send_otp(e):
                st.session_state.otp_sent = True

        if st.session_state.otp_sent:
            otp_in = st.text_input("Enter OTP")

            if st.button("Register"):
                if otp_in == st.session_state.otp:
                    if register_user(u, e, p):
                        st.success("Registered successfully")
                    else:
                        st.error("User already exists")
                else:
                    st.error("Invalid OTP")


# ---------------- MAIN ----------------
if st.session_state.user_id is None:
    login_ui()
    st.stop()

st.sidebar.success(f"👤 {st.session_state.username}")

if st.sidebar.button("Logout"):
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.group_id = None
    st.rerun()

st.title("📊 Dashboard")


# ---------------- CREATE GROUP ----------------
st.subheader("➕ Create Group")

new_group = st.text_input("Group Name")

if st.button("Create Group"):
    if new_group.strip():
        if create_group(st.session_state.user_id, new_group.strip()):
            st.success("Group created successfully")
            st.rerun()
        else:
            st.error("Failed to create group")
    else:
        st.warning("Please enter group name")


# ---------------- GROUP SELECT ----------------
groups = get_user_groups(st.session_state.user_id)

if groups.empty:
    st.warning("Create group first")
    st.stop()

group_name = st.selectbox("Select Group", groups["name"])

gid = int(groups[groups["name"] == group_name]["id"].values[0])
st.session_state.group_id = gid


# ---------------- FRIENDS ----------------
st.subheader("👥 Friends")

name = st.text_input("Friend Name")
upi = st.text_input("UPI ID")

if st.button("Add Friend"):
    if name.strip():
        if not upi.strip():
            st.warning("Please enter UPI ID")
        else:
            add_friend(st.session_state.user_id, gid, name.strip(), upi.strip())
            st.success("Friend added")
            st.rerun()
    else:
        st.warning("Please enter friend name")

friends = get_friends(st.session_state.user_id, gid)

if friends.empty:
    st.info("Add at least one friend to continue")
    st.stop()


# ---------------- EXPENSE ----------------
st.subheader("💸 Add Expense")

desc = st.text_input("Description")
amt = st.number_input("Amount", min_value=0.0)

payer = st.selectbox(
    "Paid By",
    friends["id"],
    format_func=lambda x: friends[friends["id"] == x]["name"].values[0],
)

split = st.multiselect(
    "Split Among",
    friends["id"],
    default=list(friends["id"]),
)

if st.button("Add Expense"):
    if desc.strip() and amt > 0 and len(split) > 0:
        expense_date = datetime.now().strftime("%Y-%m-%d")
        add_expense(
            st.session_state.user_id,
            gid,
            expense_date,
            desc.strip(),
            int(payer),
            float(amt),
            split,
        )
        st.success("Expense added")
        st.rerun()
    else:
        st.warning("Fill all expense details")


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
        elif v < 0:
            st.error(f"{k} owes ₹{-v:.0f}")


# ---------------- PAYMENTS ----------------
st.subheader("💳 Payments")

payments = get_payments(gid)

for _, p in payments.iterrows():
    st.write(f"{p['payer']} → {p['receiver']} : ₹{p['amount']}")

    if p["status"] == "PAID":
        st.success("Paid")
    else:
        receiver_upi = get_friend_upi(p["receiver"])
        if receiver_upi:
            link = generate_upi(p["amount"], receiver_upi, p["receiver"])
            st.link_button("Pay Now", link)
        else:
            st.warning(f"UPI not set for {p['receiver']}")

        if st.button("Mark Paid", key=p["id"]):
            mark_payment_paid(p["id"])
            st.rerun()
