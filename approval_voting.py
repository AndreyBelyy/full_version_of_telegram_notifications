# main program

import subprocess
import os
import sys
import asyncio
import datetime
import logging


from chatgptmax import send
from telethon import TelegramClient, events, Button, functions, types
from create_topic_module import check_topic_exists_in_db, create_forum_topic,insert_topic_id_and_name

# Install necessary packages
required_packages = ['telethon', 'psycopg2-binary']
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

import psycopg2

# Check for required arguments
if len(sys.argv) < 2:
    print("Usage: python script.py 'Please, make a vote'")
    sys.exit(1)
# Assuming the second command line argument is the project name


# Script configurations
voting_message = sys.argv[1]

api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
group_chat_id = int(os.getenv('GROUP_CHAT_ID', '-1001572494479'))  # Default if not set
bot_token = os.getenv('BOT_TOKEN')

client = TelegramClient('anon', api_id, api_hash).start(bot_token=bot_token)
file_path = './trivy_scan_export.txt'

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize global variables
votes = {}
before_extension_votes = {}
after_extension_votes = {}
extension_time = 0
results_announced = False

# extract the component name from the parameter message
input_str = sys.argv[1]
parts = input_str.split(' ')
topic_name = parts[1]


def read_file_content(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()
# Function to send a file to the chat
async def send_file_and_analyze():
    logging.info("Sending file to the chat and analyzing its content.")
    if os.path.exists(file_path):
        # Send SonarQube analisis
        await client.send_message(group_chat_id, f"SonarQube:\nhttps://sonar-qa.macropay.mx/dashboard?id={topic_name}", reply_to=topic_id)
        # Send the file to the chat
        await client.send_file(group_chat_id, file_path, caption='Trivy análisis',reply_to=topic_id)

        # Read the file content
        file_content = read_file_content(file_path)
        prompt = "Haga un análisis de estas vulnerabilidades y haga un resumen y que daño podría hacer, la respuesta no debe contener más de 4096 caracteres"

        # Make a single call to ChatGPT and get the response
        logging.info("Sending content to ChatGPT for analysis...")
        responses = send(prompt=prompt, text_data=file_content, chat_model="gpt-3.5-turbo")
        response_message = " ".join(responses)
        logging.info("Posting the analysis result to the Telegram group...")
        await client.send_message(group_chat_id, response_message,reply_to=topic_id)
    else:
        logging.error(f"File not found: {file_path}")
        sys.exit(1)

# Define a function to read the content of a file
def read_file_content(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

# Function to ask users to choose voting duration
async def ask_voting_duration():
    logging.info("Asking for voting duration.")
    await client.send_message(group_chat_id, "Choose the duration for voting:", buttons=[
        [Button.inline('1 min', b'1min'), Button.inline('3 min', b'3min')],
        [Button.inline('5 min', b'5min'), Button.inline('10 min', b'10min')]
    ], reply_to=topic_id)

# Function to send the voting message with buttons
async def send_voting_message():
    logging.info("Sending voting message.")
    await client.send_message(group_chat_id, voting_message, buttons=[
        [Button.inline('Approve', b'approve'), Button.inline('Decline', b'decline')]
    ], reply_to=topic_id)

# Callback handler for handling all button clicks
@client.on(events.CallbackQuery)
async def callback_handler(event):
    user = await event.get_sender()
    user_id = user.id
    data = event.data.decode('utf-8')

    if data.endswith('min'):
        await duration_handler(event, user_id, data)
    elif data in ['approve', 'decline', 'yes', 'no']:
        await handle_vote(event, user_id, data, user)

# Function to handle duration setting
async def duration_handler(event, user_id, duration_choice):
    global extension_time
    logging.info(f"Handling duration setting: {duration_choice}")
    message = await event.get_message()

    if user_id in [483998347, 1535811250, 6844472834, 1879912673, 6344966192, 6734209508]:
        duration_minutes = int(duration_choice[:-3])
        extension_time = int(datetime.datetime.now().timestamp()) + (duration_minutes * 60)
        await message.edit(f"Voting duration set to {duration_minutes} minutes. Starting voting...", buttons=None)
        await send_voting_message()
    else:
        await event.answer("You're not authorized to set the duration.")

# Function to handle votes
async def handle_vote(event, user_id, vote, user):
    global votes, before_extension_votes, after_extension_votes, extension_time
    logging.info(f"Handling vote: {vote} by user {user_id}")
    current_timestamp = int(datetime.datetime.now().timestamp())
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else "no username"
    choice_text = 'approved' if vote == 'approve' else 'declined'

    if vote in ['approve', 'decline']:
        if user_id not in votes or user_id in [483998347, 1535811250, 6844472834, 1879912673, 6344966192, 6734209508]:
            votes[user_id] = vote
            if current_timestamp < extension_time:
                before_extension_votes[user_id] = vote
            else:
                after_extension_votes[user_id] = vote
            public_message = f"{full_name} ({username}) has {choice_text} the proposal."
            await client.send_message(group_chat_id, public_message, reply_to=topic_id)
            await event.answer(f"You have {choice_text} the proposal.")
        else:
            await event.answer("You have already voted.")

# Function to announce results
async def announce_results():
    global results_announced
    if not results_announced:
        logging.info("Announcing results.")
        results_announced = True
        combined_votes = {**before_extension_votes, **after_extension_votes}
        approve_count = sum(1 for v in combined_votes.values() if v == 'approve')
        decline_count = sum(1 for v in combined_votes.values() if v == 'decline')
        results_message = f"Voting results:\nApprove: {approve_count}\nDecline: {decline_count}"
        await client.send_message(group_chat_id, results_message,reply_to=topic_id)
        photo_path = 'approve.png' if approve_count > decline_count else 'decline.png'
        await client.send_file(group_chat_id, photo_path,reply_to=topic_id)
        sys.exit(0 if approve_count > decline_count else 1)

# Main function to run the script
async def main():

    client = TelegramClient('session', api_id, api_hash)
    logging.info("Starting the client.")
    # Ensure the client is properly referenced and awaited when started
    await client.start(bot_token=bot_token)
    # Check if the topic exists or create a new one
    global topic_id
    topic_id = check_topic_exists_in_db(topic_name)
    if topic_id:
        logger.info(f"Topic '{topic_name}' already exists in the database with ID {topic_id}.")
    else:
        logger.info(f"Topic '{topic_name}' does not exist in the database. Creating it.")
        # Create the topic since it does not exist
        created_topic_name, created_topic_id = await create_forum_topic(client, group_chat_id, topic_name)
        if created_topic_id:
            # Insert the new topic into the database
            insert_topic_id_and_name(created_topic_id, created_topic_name)
            logger.info(f"Successfully created topic '{created_topic_name}' with ID {created_topic_id}.")
            topic_id = created_topic_id  # Update topic_id to use for further operations
        else:
            logger.error(f"Failed to create the topic '{topic_name}'.")
            return  # Or handle the failure as needed
    with open("topic_id.txt", "w") as f:
        f.write(str(topic_id))
        logger.info(f"Successfully wrote topic ID {topic_id} to file 'topic_id.txt'.")
    
    logging.info("Starting the client.")

    await send_file_and_analyze()
    await ask_voting_duration()

    # Wait until extension_time is set
    while extension_time == 0:
        await asyncio.sleep(1)

    logging.info("Voting period has started.")
    while int(datetime.datetime.now().timestamp()) < extension_time:
        await asyncio.sleep(1)

    if not results_announced:
        await announce_results()

    logging.info("Voting concluded. Disconnecting the client.")
    await client.disconnect()

if __name__ == '__main__':
    logging.info("Running the main function.")
    client.loop.run_until_complete(main())
    logging.info("Main function has completed.")
