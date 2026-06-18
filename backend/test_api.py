import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Since we removed auth, we don't need tokens
        resp = await client.post("http://127.0.0.1:8000/api/interview/start")
        print("Status:", resp.status_code)
        print("Body:", resp.text)

if __name__ == "__main__":
    asyncio.run(test())
