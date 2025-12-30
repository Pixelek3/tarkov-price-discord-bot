# Tarkov Price Check Bot 🛒

Discord bot designed for **Escape from Tarkov** players. It allows for quick item price checking by analyzing screenshots (OCR). The bot recognizes text in the image, identifies items, and fetches their current prices from the Flea Market using the [tarkov.dev](https://tarkov.dev/) API.

## ✨ Features

* **OCR (Optical Character Recognition):** Uses the `PaddleOCR` engine to read item names from inventory photos.
* **Smart Matching:** Thanks to the Levenshtein algorithm (Fuzzy Search), the bot handles typos and OCR errors.
* **Live Prices:** Fetches average prices from the last 24h and the lowest prices from the Flea Market.
* **Change Indicators:** Shows percentage price change (colored using ANSI codes in Discord).
* **Security:** Supports environment variables (`.env`) for token protection.

## ⚙️ Requirements

* Python 3.8 or newer
* Discord Developer Account (to create the bot)
* Operating System: Windows / Linux / macOS

## 📥 Installation

1.  **Download code**
    Clone this repository or download files to a folder.

2.  **Install required libraries**
    Open terminal in the bot folder and run:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: `paddlepaddle` installation may take a while as the library is quite large).*

3.  **Configure .env file**
    Create a file named `.env` in the main folder and paste the content below, replacing the token with yours:
    ```env
    DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE
    ```

## 🚀 Running

To start the bot, type in the terminal:

```bash
python main.py
```
If successful, you will see the message:
`Logged in as [YourBotName]`

## 🎮 How to use?

1. Go to a channel where the bot is present (or DM it).
2. Drag and drop a screenshot of your inventory (or stash) into the chat window.
3. In the message box (along with the image), type the command:
```!c```
4. The bot will analyze the image and reply with a list of found items and their prices.

## 🔧 Discord Developer Portal Configuration

For the bot to work correctly, you must enable specific permissions in the Discord Developer Portal:

1. Go to [Discord Developer Portal](https://discord.com/developers/applications).
2. Select your application -> **Bot** tab.
3. In the **Privileged Gateway Intents** section, check:
 * ✅ **Message Content Intent** (Crucial for reading attachments and command content).
 * ✅ **Server Members Intent** (Recommended).
 * ✅ **Presence Intent** (Recommended).

## ❗ Troubleshooting

* **"Microsoft Visual C++ 14.0 is required" error**:
This may appear when installing `Levenshtein` on Windows. You need to install "Build Tools for Visual Studio" with C++ support.
* **Bot not responding to command**:
Ensure you enabled **Message Content Intent** in the Discord panel (see section above).
* **Poor recognition quality**:
The bot works best with clear screenshots, and worse with photos taken by a phone.

## 📚 Libraries

This project uses the following open-source solutions:
* [Discord.py](https://github.com/Rapptz/discord.py)
* [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
* [Tarkov.dev API](https://tarkov.dev/api/)