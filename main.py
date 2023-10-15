import os
import requests
import telebot
from flask import Flask, request
from gunicorn_config import bind, workers  # Import the Gunicorn configuration

# Replace these with your Telegram bot API token and Shotcut.in API token
TELEGRAM_BOT_API_TOKEN = "YOUR_TELEGRAM_BOT_API_TOKEN"
SHOTCUT_IN_API_TOKEN = "YOUR_SHOTCUT_IN_API_TOKEN"

# Set the maximum number of links a user can shorten for free
MAX_FREE_LINKS = 7

# Create a Flask app
app = Flask(__name__)

# Create a Telegram bot object
bot = telebot.TeleBot(TELEGRAM_BOT_API_TOKEN)

# Dictionary to keep track of user states and the number of links they've shortened
user_states = {}
user_link_counts = {}

# Define user states
WAITING_FOR_URL = 1
WAITING_FOR_MORE = 2

# Function to shorten a URL using the Shotcut.in API
def shorten_url(url):
    headers = {
        "Authorization": f"Bearer {SHOTCUT_IN_API_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "url": url,
    }
    response = requests.post("https://shotcut.in/api/url/add", headers=headers, json=data)
    response_json = response.json()
    if response.status_code != 200:
        error_message = response_json.get("message", "Unknown error")
        return None, error_message
    elif response_json["error"] == 0:
        short_url = response_json["shorturl"]
        return short_url, None
    else:
        return None, "Failed to shorten URL"

# Define a route for the Telegram webhook
@app.route(f'/{TELEGRAM_BOT_API_TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '', 200

# Function to handle the /start command
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id

    # Set the user's state to WAITING_FOR_URL
    user_states[user_id] = WAITING_FOR_URL

    # Send the initial greeting message
    bot.send_message(user_id, "Hi! I'm a Shotcut.in' bot. Please send me the URL you'd like to shorten.")

# Function to handle incoming Telegram messages
@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == WAITING_FOR_URL)
def handle_message(message):
    user_id = message.chat.id
    url = message.text

    # Check if the user has reached the link limit
    link_count = user_link_counts.get(user_id, 0)
    if link_count >= MAX_FREE_LINKS:
        bot.send_message(user_id, f"You have reached the limit of free shortened links. To shorten more links, consider creating an account on Shotcut.in.")
        user_states[user_id] = None
    else:
        # Shorten the URL using the Shotcut.in API
        short_url, error_message = shorten_url(url)

        if short_url is not None:
            bot.send_message(user_id, f"Here is your shortened URL: {short_url}")

            # Increment the link count for the user
            link_count = user_link_counts.get(user_id, 0) + 1
            user_link_counts[user_id] = link_count

            if link_count < MAX_FREE_LINKS:
                bot.send_message(user_id, f"You have shortened {link_count} out of {MAX_FREE_LINKS} free links. Do you want to shorten more links? Yes or No?")
                user_states[user_id] = WAITING_FOR_MORE
            else:
                bot.send_message(user_id, f"You have reached the limit of free shortened links ({MAX_FREE_LINKS}). To shorten more links, consider creating an account on Shotcut.in.")
                user_states[user_id] = None
        else:
            bot.send_message(user_id, f"{error_message} Please try again.")

# Function to handle user response to shorten more links
@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == WAITING_FOR_MORE)
def handle_more_links(message):
    user_id = message.chat.id
    response = message.text.lower()
    
    if response == "yes":
        # Set the user's state to WAITING_FOR_URL
        user_states[user_id] = WAITING_FOR_URL
        bot.send_message(user_id, "Great! Please send me the URL you'd like to shorten.")
    else:
        # Reset the user's state
        user_states[user_id] = None
        bot.send_message(user_id, "Thank you for using the URL shortener bot. If you have more links to shorten, feel free to ask anytime! And for making QR codes, bio pages, and managing your shortened links, visit Shotcut.in")

if __name__ == '__main__':
    app.run(debug=True)
