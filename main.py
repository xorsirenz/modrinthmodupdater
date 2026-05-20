import os
import asyncio
import hashlib
import aiohttp

from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=8)

def hash_file(path):
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()

def write_file(path, content):
    with open(path, "wb") as f:
        f.write(content)

async def download_mod(session, version, file_name, backup_path, mods_path):
    try:
        jar_file = os.path.join(backup_path, file_name)

        loop = asyncio.get_running_loop()
        hashed_file = await loop.run_in_executor(
            executor,
            hash_file,
            jar_file
        )

        async with session.post(
            url = "https://api.modrinth.com/v2/version_files/update",
            headers = {
                "User-Agent": "just updating mods",
                "Content-Type": "application/json"
            },
            json={
                "hashes": [hashed_file],
                "algorithm": "sha1",
                "loaders": ["fabric"],
                "game_versions": [version]
            }
        ) as r:
            response = await r.json()

        if not response:
            print(f"[-] unable to update: {file_name}")
            return

        for _, value in response.items():
            file_info = value["files"][0]
            url = file_info["url"]
            filename = file_info["filename"]

            print(f"[+] downloading: {filename}")

            async with session.get(url) as download:
                content = await download.read()

            updated_mod = os.path.join(mods_path, filename)
            await loop.run_in_executor(
                executor,
                write_file,
                updated_mod,
                content
            )

    except Exception as e:
        print(f"[!] error processing {file_name}: {e}")

async def main():
    version = input("mc version: ")
    mods_path = os.path.expanduser("mods/")
    backup_path = os.path.expanduser("mods.bak/")

    if not os.path.exists(backup_path):
        print(f"creating {backup_path}")
        os.mkdir(backup_path)

    files = os.listdir(mods_path)
    jar_files = []

    for file_name in files:
        if file_name.endswith(".jar"):
            src_path = os.path.join(mods_path, file_name)
            dst_path = os.path.join(backup_path, file_name)
            os.rename(src_path, dst_path)
            jar_files.append(file_name)

    connector = aiohttp.TCPConnector(limit=20)

    async with aiohttp.ClientSession(
        connector=connector
    ) as session:
        tasks = [
            download_mod(
                session,
                version,
                file_name,
                backup_path,
                mods_path
            )
            for file_name in jar_files
        ]

        await asyncio.gather(*tasks)

    executor.shutdown(wait=True)

    print("[*] all downloads complete")


if __name__ == "__main__":
    asyncio.run(main())
