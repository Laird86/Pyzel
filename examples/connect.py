import asyncio

from pyzel import ZelloClient


async def main():
    client = ZelloClient(username="example-user", password="example-password")

    connected = await client.connect()
    print(f"Connected: {connected}")

    logon_payload = await client.join_channel("ExampleChannel")
    print(f"Logon payload: {logon_payload}")

    text_payload = await client.send_text_message("Hello from Pyzel")
    print(f"Text payload: {text_payload}")

    ping_payload = await client.ping()
    print(f"Ping payload: {ping_payload}")

    disconnected = await client.disconnect()
    print(f"Disconnected: {disconnected}")


if __name__ == "__main__":
    asyncio.run(main())
