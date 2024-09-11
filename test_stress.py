import asyncio
import random
import string
import time

from httpx import AsyncClient


def generate_random_string(length: int) -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))


async def make_request(client: AsyncClient) -> bool:
    try:
        r = await client.post(
            'http://0.0.0.0:8000/api/v1/user/',
            json={
                'username': generate_random_string(10),
                'password': generate_random_string(10)
            }
        )
        if r.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        print(str(e))
        return False


async def stress_test(num_requests):
    async with AsyncClient() as client:
        tasks = [make_request(client) for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
    return results


async def main():
    num_requests = 500
    start_time = time.time()

    results = await stress_test(num_requests)

    end_time = time.time()
    duration = end_time - start_time
    successful = sum(1 for r in results if r)
    failed = num_requests - successful

    print(f"Stress test completed in {duration:.2f} seconds")
    print(f"Total requests: {num_requests}")
    print(f"Successful requests: {successful}")
    print(f"Failed requests: {failed}")
    print(f"Requests per second: {num_requests / duration:.2f}")


if __name__ == '__main__':
    asyncio.run(main())
