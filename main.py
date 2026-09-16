import asyncio

from gryfsmartio.transport import Transport

async def main():
    transport = Transport("192.168.40.72")
    transport.start_communication()

    await asyncio.sleep(2)

    while True:
        transport.write("SetLED=1,3,100")
        await asyncio.sleep(3)
        transport.write("SetLED=1,3,0")
        await asyncio.sleep(3)
        

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n")
