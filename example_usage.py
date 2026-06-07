import asyncio
import logging
from pyzello import ZelloClient

# Setup basic logging to see PyZello's internal messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    # Configure your credentials here
    config = {
        "auth_mode": "development", # Switch to "production" to use JWT
        "auth_token": "YOUR_DEVELOPMENT_TOKEN_HERE", # Or zello_password
        "zello_username": "YOUR_USERNAME",
        "zello_channels": ["TestChannel"]
    }

    # Initialize client
    client = ZelloClient(api_config=config)

    # Attach event handlers
    def handle_connect():
        print(">>> Callback: Successfully connected to Zello!")
        
    def handle_event(event_data):
        command = event_data.get('command')
        if command not in ["on_channel_status", "on_users_list"]:
            print(f">>> Callback: Received Event: {command}")

    client.on_connect = handle_connect
    client.on_event = handle_event

    # Connect in the background
    connection_task = asyncio.create_task(client.connect())
    
    # Wait for connection to establish
    await asyncio.sleep(5)
    
    # Send a private message (if applicable)
    # await client.send_private_message("Hello from the python SDK!", "AdminUser")

    # Send a message to the channel
    if client.is_connected:
        await client.send_text_message("Automated message from PyZello SDK!", "TestChannel")

    # Keep script alive to continue listening
    try:
        await connection_task
    except KeyboardInterrupt:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
