import subprocess
import os
import sys
import asyncio
import datetime
from telethon import TelegramClient, events, Button
import logging
# Function to check and install the required package

def install_package(package):
    try:
        __import__(package)
    except ImportError as e:
        print(f"Package {package} not found, installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Check and install Telethon if needed
install_package("telethon")

# Define the necessary credentials
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
group_chat_id = int(os.getenv('GROUP_CHAT_ID', '-1001572494479'))  # Default if not set
bot_token = os.getenv('BOT_TOKEN')

# Initialize the client
client = TelegramClient('anon', api_id, api_hash)

# Get topic_id
with open("topic_id.txt", "r") as f:
    topic_id = int(f.read().strip())

# Function to send a message to topic
async def send_message(text):
    async with client:
        await client.send_message(group_chat_id, text, reply_to=topic_id)

# The text message to send, passed as a command line argument
message_text = ' '.join(sys.argv[1:])  # Joins all arguments into a single string

# Run the client and send the message
client.loop.run_until_complete(send_message(message_text))
