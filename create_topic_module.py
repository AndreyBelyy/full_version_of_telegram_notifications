#create topic module

from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest, CreateForumTopicRequest
from telethon.tl.types import InputChannel, MessageActionTopicCreate
import subprocess
import os
import sys
import asyncio
import datetime
import logging
import socket

# Install necessary packages
required_packages = ['telethon', 'psycopg2-binary']
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

import psycopg2

api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
group_chat_id = int(os.getenv('GROUP_CHAT_ID', '-1001572494479'))  # Default if not set
bot_token = os.getenv('BOT_TOKEN')

db_name = os.getenv('DB_NAME')
db_user = os.getenv('DB_USERNAME')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
                    
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

async def fetch_channel_info(client, channel_id):
    logger.info(f"Fetching channel info for channel_id: {channel_id}")
    try:
        channel = await client.get_entity(channel_id)
        logger.info(f"Successfully fetched channel info: {channel.id}, {channel.access_hash}")
        return channel.id, channel.access_hash
    except Exception as e:
        logger.error(f"Error fetching channel info: {e}")
        raise

def check_topic_exists_in_db(topic_name):
    conn = None
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host=db_host)

        # Resolve the hostname to an IP address
        try:
            ip_address = socket.gethostbyname(db_host)
            logger.info(f"Successfully connected to database at {db_host} (IP: {ip_address})")
        except socket.gaierror:
            logger.info(f"Successfully connected to database at {db_host}, but could not resolve IP address.")

        cur = conn.cursor()
        cur.execute('SELECT topic_id FROM topics_ids WHERE topic_name = %s LIMIT 1;', (topic_name,))
        result = cur.fetchone()
        if result:
            # Return the topic_id if found
            return result[0]
        else:
            return None
    except Exception as error:
        logger.error(f"Error connecting to the database: {error}")
    finally:
        if conn is not None:
            conn.close()


async def create_forum_topic(client, channel_id, topic_name):
    logger.info(f"Creating forum topic '{topic_name}' in channel_id: {channel_id}")
    try:
        channel_id, access_hash = await fetch_channel_info(client, channel_id)
        input_channel = InputChannel(channel_id, access_hash)
        result = await client(CreateForumTopicRequest(
            channel=input_channel,
            title=topic_name,
            # Assuming default values for optional parameters; customize as needed
        ))

        # Iterate through the updates to find the UpdateNewChannelMessage with the forum topic creation action
        for update in result.updates:
            if hasattr(update, "message") and hasattr(update.message, "action") and isinstance(
                    update.message.action, MessageActionTopicCreate):
                created_topic_id = update.message.id
                created_topic_title = update.message.action.title
                logger.info(f"Forum topic created with ID: {created_topic_id} and title: '{created_topic_title}'")
                return created_topic_title, created_topic_id

        logger.warning(f"No updates found for created forum topic '{topic_name}'")
        return None, None

    except Exception as e:
        logger.error(f"Error creating forum topic '{topic_name}': {e}")
        return None, None

def insert_topic_id_and_name(topic_id, topic_name):
    logger.info(f"Inserting topic_id: {topic_id}, topic_name: '{topic_name}' into database")
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host=db_host)
        cur = conn.cursor()
        cur.execute('INSERT INTO topics_ids (topic_id, topic_name) VALUES (%s, %s) ON CONFLICT (topic_id) DO NOTHING;',
                    (topic_id, topic_name))
        conn.commit()
        logger.info("Successfully inserted topic into database")
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"Error inserting topic into database: {error}")
    finally:
        if conn is not None:
            conn.close()

async def main():
    async with TelegramClient('session3', api_id, api_hash) as client:
        # Now, properly start the client with the bot token
        await client.start(bot_token=bot_token)
        topic_name = topic_name_create  # The topic name you want to create

        # Check if the topic already exists in the database and retrieve its ID if it does
        existing_topic_id = check_topic_exists_in_db(topic_name)
        if existing_topic_id:
            logger.info(f"Topic '{topic_name}' already exists in the database with ID {existing_topic_id}.")
            # Use existing_topic_id for further operations
        else:
            logger.info(f"Topic '{topic_name}' does not exist in the database. Proceeding with creation.")
            created_topic_name, created_topic_id = await create_forum_topic(client, channel_id, topic_name)

            if created_topic_name and created_topic_id:
                # If topic creation was successful, insert it into the database
                insert_topic_id_and_name(created_topic_id, created_topic_name)
                logger.info(f"Successfully created topic '{created_topic_name}' with ID {created_topic_id} and inserted it into the database.")
                # Use created_topic_id for further operations
            else:
                logger.error("Failed to create the forum topic or obtain its ID and name.")



if __name__ == "__main__":
    asyncio.run(main())
