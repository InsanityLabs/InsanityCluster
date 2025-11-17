from dotenv import load_dotenv
import os

load_dotenv()

print(f"Host: {os.getenv('POSTGRES_HOST')}")
print(f"User: {os.getenv('POSTGRES_USER')}")
print(f"DB: {os.getenv('POSTGRES_DB')}")
print(f"Pass: {os.getenv('POSTGRES_PASSWORD')}")
