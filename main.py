import requests
import time
import re
from langdetect import detect
from cachetools import TTLCache
from ratelimit import limits, sleep_and_retry

# Set API credentials for Together AI's LLaMA 3.1 8B model
API_KEY = "6f92d9224169189b4e64ae9dfc272f4256a2dbc2987ff1faa64dcb17bec4babd"
LLAMA_API_URL = "https://api.together.xyz/models/meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"

# Set API URL for CoinGecko (Cryptocurrency Prices)
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"

# Create a cache to store prices for 5 minutes (300 seconds)
cache = TTLCache(maxsize=100, ttl=300)


# Rate limit to 60 requests per minute for the CoinGecko API
@sleep_and_retry
@limits(calls=60, period=60)
def get_crypto_price(crypto: str, currency: str = "usd"):
    """Fetches the current price of the cryptocurrency from CoinGecko."""
    if crypto in cache:
        return cache[crypto]

    try:
        response = requests.get(f"{COINGECKO_API_URL}?ids={crypto}&vs_currencies={currency}")
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.text  # Directly using the raw response text instead of JSON
        # Parse the raw response manually (assuming CoinGecko returns the correct format)
        if f'"{crypto}":' in data:
            price_start = data.find(f'"{crypto}":') + len(f'"{crypto}":')
            price_end = data.find('"usd":', price_start) + len('"usd":')
            price_value_end = data.find(',', price_end)
            price = data[price_end:price_value_end].strip()
            cache[crypto] = price  # Cache the result
            return price
        else:
            return "Cryptocurrency not found."
    except requests.exceptions.RequestException as e:
        return f"Error fetching price: {e}"


# Set up API credentials for LLaMA (Together AI)
def get_llama_response(prompt: str):
    """Interacts with Together AI's LLaMA 3.1 8B model."""
    response = requests.post(
        LLAMA_API_URL,
        headers={"Authorization": f"Bearer {API_KEY}"},
        data={'input': prompt}  # Using 'data' instead of 'json' to avoid JSON encoding
    )

    if response.status_code == 200:
        return response.text  # Return raw text instead of parsed JSON
    else:
        return "Sorry, there was an error getting the response."


class ChatBot:
    """Handles maintaining context across multiple user messages."""

    def __init__(self):
        self.context = ""

    def update_context(self, user_input: str, bot_response: str):
        """Updates the context with user input and bot response."""
        self.context += f"User: {user_input}\nBot: {bot_response}\n"

    def get_bot_response(self, user_input: str):
        """Gets a response from LLaMA while maintaining context."""
        self.update_context(user_input, "")
        full_prompt = self.context + f"User: {user_input}\nBot:"
        bot_response = get_llama_response(full_prompt)
        self.update_context(user_input, bot_response)
        return bot_response


class CryptoBot:
    """Main class that handles user input, cryptocurrency queries, and language change."""

    def __init__(self):
        self.chatbot = ChatBot()

    def detect_language(self, text: str):
        """Detects the language of the user input."""
        return detect(text)

    def translate_to_english(self, text: str):
        """Ensures the bot responds in English, no matter the user's input language."""
        detected_language = self.detect_language(text)
        if detected_language != 'en':
            # For simplicity, returning a fixed message here; you can integrate a translation service.
            return "I can only respond in English."
        return text

    def handle_query(self, user_input: str):
        """Handles cryptocurrency price queries and basic interactions."""
        crypto_match = re.search(r"(bitcoin|ethereum|dogecoin|litecoin|bnb|xrp)", user_input, re.IGNORECASE)

        if crypto_match:
            crypto_name = crypto_match.group(0).lower()
            price = get_crypto_price(crypto_name)
            return f"The current price of {crypto_name} is {price}."
        return "Sorry, I didn't catch which cryptocurrency you are asking about."

    def respond(self, user_input: str):
        """Generates bot response, including handling language change and crypto queries."""
        # First handle language change
        if "change language" in user_input.lower():
            return "All responses will be in English."

        # Translate user input if needed
        user_input = self.translate_to_english(user_input)

        # Handle cryptocurrency query
        response = self.handle_query(user_input)
        if "cryptocurrency" in response.lower():
            return response

        # Get response from LLaMA
        bot_response = self.chatbot.get_bot_response(user_input)
        return bot_response


# Example Usage
crypto_bot = CryptoBot()

# Simulating conversation with user:
user_input = "What is the price of Bitcoin?"
response = crypto_bot.respond(user_input)
print(response)

user_input = "Can you tell me the price of Ethereum?"
response = crypto_bot.respond(user_input)
print(response)

user_input = "¿Cuál es el precio de Dogecoin?"
response = crypto_bot.respond(user_input)
print(response)  # Should print in English despite Spanish input

user_input = "change language"
response = crypto_bot.respond(user_input)
print(response)
