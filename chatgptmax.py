# chatgptmax module
from openai import OpenAI, AuthenticationError, RateLimitError
import time
import random
import subprocess
import sys
import os

required_packages = ['openai']
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        
# Set up your OpenAI API key
api_key = os.getenv('API_KEY')
client = OpenAI(api_key=api_key)

def exponential_backoff(request_func, *args, **kwargs):
    """
    Implements exponential backoff retrying for rate limited requests.
    """
    max_attempts = 5
    base_delay = 1  # Base delay in seconds
    for attempt in range(max_attempts):
        try:
            return request_func(*args, **kwargs)
        except RateLimitError as e:
            if attempt < max_attempts - 1:
                # Calculate delay with exponential backoff and random jitter
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"Rate limit exceeded, retrying in {delay:.2f} seconds...")
                time.sleep(delay)
            else:
                print("Max retry attempts reached. Aborting.")
                raise e
        except AuthenticationError as e:
            print("Authentication failed. Check your API key.")
            raise e

def send(prompt=None, text_data=None, chat_model="gpt-3.5-turbo", max_chars=15000):
    if not prompt:
        return "Error: Prompt is missing. Please provide a prompt."
    if not text_data:
        return "Error: Text data is missing. Please provide some text data."

    # Split the text_data into chunks based on max_chars
    chunks = [text_data[i:i + max_chars] for i in range(0, len(text_data), max_chars)]

    responses = []
    messages = [{"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}]

    for chunk in chunks:
        messages.append({"role": "user", "content": chunk})
        # Use exponential_backoff wrapper to handle rate limits
        response = exponential_backoff(client.chat.completions.create, model=chat_model, messages=messages)
        chatgpt_response = response.choices[0].message.content.strip()  # Corrected line
        responses.append(chatgpt_response)

    return responses
