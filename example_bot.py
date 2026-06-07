import asyncio
import logging
from pyzel import ZelloClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    config = {
        "auth_mode": "development", 
        "auth_token": "YOUR_DEVELOPMENT_TOKEN", 
        "zello_username": "YOUR_USERNAME",
        "zello_channels": ["TestChannel"]
    }

    client = ZelloClient(api_config=config)

    # 1. Listen for connection success
    @client.on("connect")
    async def on_connect():
        print(">>> Bot is online!")

    # 2. Build a simple "Echo Bot"
    @client.on("on_text_message")
    async def handle_text_message(event):
        """
        Triggered when someone sends a text to the channel or direct message.
        """
        sender = event.get("from")
        text = event.get("text", "")
        channel = event.get("channel")

        # Prevent the bot from replying to itself
        if sender == config["zello_username"]:
            return

        print(f"[{channel}] {sender} says: {text}")

        # Echo the message back to the channel
        if "echo" in text.lower():
            reply = f"Hello {sender}! I heard you say: {text}"
            await client.send_text_message(reply, channel)

    # Run the client in the background
    try:
        print("Starting bot...")
        await client.start()
    except KeyboardInterrupt:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
