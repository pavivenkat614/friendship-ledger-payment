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
    st.session_state.otp = otp

    if get_otp_delivery_mode() == "debug":
        st.info(f"Debug OTP: {otp}")
        return True

    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")

    if not sender or not password:
        st.error("Email config missing")
        return False

    msg = f"Subject: OTP\n\nYour OTP is {otp}"

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as s:
            s.starttls()
            s.login(sender, password)
            s.sendmail(sender, email, msg)
        return True
    except Exception as e:
        st.error(f"OTP failed: {str(e)}")
        return False


# ---------------- LOGIN UI ----------------
def login_ui():
    st.title("💰 Friendship Ledger")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        u = st.text_input("Username / Email")
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
                    result = register_user(u, e, p)

            if result is True:
                st.success("Registered successfully")
            else:
                st.error(result)

        else:
            st.error("Invalid OTP")
                
if st.session_state.user_id is None:
    login_ui()
    st.stop()


# ---------------- SIDEBAR ----------------
st.sidebar.success(f"👤 {st.session_state.username}")

if st.sidebar.button("Logout"):
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.group_id = None
    st.rerun()


# ---------------- DASHBOARD ----------------
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
        st.warning("Enter group name")


# ---------------- GROUP SELECT ----------------

groups = get_user_groups(st.session_state.user_id)

if groups.empty:
    st.warning("Create group first")
    st.stop()

group_map = {
    row["id"]: row["name"]
    for _, row in groups.iterrows()
}

gid = st.selectbox(
    "Select Group",
    options=list(group_map.keys()),
    format_func=lambda x: group_map[x]
)

st.session_state.group_id = gid

# ---------------- FRIENDS ----------------
st.subheader("👥 Friends")

fname = st.text_input("Friend Name")
upi = st.text_input("UPI ID")

if st.button("Add Friend"):
    if fname.strip() and upi.strip():
        if add_friend(st.session_state.user_id, gid, fname.strip(), upi.strip()):
            st.success("Friend added")
            st.rerun()
        else:
            st.error("Failed to add friend")
    else:
        st.warning("Enter all details")

friends = get_friends(st.session_state.user_id, gid)

if friends.empty:
    st.info("Add at least one friend")
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
        add_expense(
            st.session_state.user_id,
            gid,
            datetime.now().strftime("%Y-%m-%d"),
            desc.strip(),
            int(payer),
            float(amt),
            split,
        )
        st.success("Expense added")
        st.rerun()
    else:
        st.warning("Fill all fields")


# ---------------- EXPENSE TABLE ----------------
df = get_expenses(st.session_state.user_id, gid)
st.subheader("📋 Expenses")
st.dataframe(df, width="stretch")
