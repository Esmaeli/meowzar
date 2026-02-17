import requests
import subprocess
import time
import json
import os
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed

TIMEOUT = 3
MAX_CONFIGS = 5000
MAX_RESULTS = 100
SOCKS_PORT = 10808

TEST_IPS = [
    "109.122.245.39",
    "185.24.253.139",
    "185.105.238.209",
    "178.239.146.199"
]

def fetch_subscriptions():
    configs = []
    with open("sub.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        try:
            r = requests.get(url, timeout=10)
            lines = r.text.splitlines()
            for line in lines:
                if line.startswith("vless://"):
                    configs.append(line.strip())
        except:
            pass

    return configs[:MAX_CONFIGS]

def build_config(vless_link):
    return {
        "log": {"loglevel": "none"},
        "inbounds": [{
            "port": SOCKS_PORT,
            "listen": "127.0.0.1",
            "protocol": "socks",
            "settings": {"udp": False}
        }],
        "outbounds": [{
            "protocol": "vless",
            "settings": {
                "vnext": []
            }
        }]
    }

def run_xray(config_json):
    with open("temp.json", "w") as f:
        json.dump(config_json, f)

    process = subprocess.Popen(
        ["./xray", "-config", "temp.json"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(1)
    return process

def test_proxy():
    proxies = {
        "http": f"socks5h://127.0.0.1:{SOCKS_PORT}",
        "https": f"socks5h://127.0.0.1:{SOCKS_PORT}"
    }

    success = 0

    for ip in TEST_IPS[:3]:
        try:
            requests.get(f"http://{ip}", proxies=proxies, timeout=TIMEOUT)
            success += 1
        except:
            pass

    return success >= 2

def test_config(vless_link):
    try:
        config = build_config(vless_link)
        process = run_xray(config)

        ok = test_proxy()

        process.send_signal(signal.SIGTERM)
        process.kill()

        if ok:
            return vless_link
    except:
        pass
    return None

def main():
    configs = fetch_subscriptions()
    results = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(test_config, c) for c in configs]

        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
                if len(results) >= MAX_RESULTS:
                    break

    with open("result.txt", "w") as f:
        for r in results:
            f.write(r + "\n")

if __name__ == "__main__":
    main()
