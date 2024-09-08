# DOGS_SELL Telegram Bot

## Description

DOGS_SELL Bot is a Telegram bot designed to facilitate the sale of DOGS cryptocurrency. Users can request a wallet number for sending their DOGS coins and then receive an equivalent amount of money from moderators. The bot also supports features such as leaving reviews, contacting support, checking balances, and receiving referral links.

The bot is built using the `python-telegram-bot` library and includes data synchronization mechanisms via `Lock` to ensure safe access to data files.

## Key Features

- **Class `User`**: Handles user initialization and stores all necessary attributes for each user.
- **Data Saving and Loading**:
  - `load_file` and `save` — functions to load and save the list of users in memory.
  - `load_bot_values` and `save_bot_values` — functions to manage bot configuration (such as coin rate, minimum withdrawal balance, channel links) stored in `bot_values.json`.
- **Data Synchronization**: Utilizes the `Lock` mechanism to safely access the data files across multiple threads.
- **Core Bot Commands**:
  - `/start` — Checks the user's subscription to a specific channel and initializes bot logic.
  - `/check` — Allows moderators to verify and update key bot values, such as the coin rate, withdrawal limits, and more.
  - Handlers for messages and button clicks where the main bot logic is implemented.

## Installation

### 1. Clone the repository:
```bash
git clone https://github.com/AntonShkvir/dogs-sell-bot.git
```
### 2. Navigate to the project directory:
```bash
cd dogs-crypto-bot
 ```

### 3. Install the dependencies: 
```bash 
pip install -r requirements.txt
```

### 4. Set up the configuration:
Create a `config.py` file in the root directory of your project and add your Telegram bot API token:
```python
API_TOKEN = "your_api_token_here"
```
Also, make sure you have a `bot_values.json` file with your own settings.

### 5. Run the bot:
```bash
python main.py
```