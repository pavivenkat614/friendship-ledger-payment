import psycopg2

conn = psycopg2.connect(
    host="127.0.0.1",
    database="friendship_ledger",
    user="postgres",
    password="Pavivenkat@123",
    port="5432"
)

print("Connected!")


