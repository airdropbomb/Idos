from aiohttp import (
    ClientResponseError,
    ClientSession,
    ClientTimeout,
    BasicAuth
)
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_hex
from base64 import urlsafe_b64decode
from datetime import datetime
from colorama import *
import asyncio, json, re, os, pytz

wib = pytz.timezone('Asia/Jakarta')

class idOS:
    def __init__(self) -> None:
        self.BASE_API = "https://app.idos.network/api"
        self.HEADERS = {}
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.user_ids = {}
        self.access_tokens = {}

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}",
            flush=True
        )

    def welcome(self):
        print(
            f"""
            {Fore.GREEN + Style.BRIGHT}        █████╗ ██████╗ ██████╗     ███╗   ██╗ ██████╗ ██████╗ ███████╗
            {Fore.GREEN + Style.BRIGHT}       ██╔══██╗██╔══██╗██╔══██╗    ████╗  ██║██╔═══██╗██╔══██╗██╔════╝
            {Fore.GREEN + Style.BRIGHT}       ███████║██║  ██║██████╔╝    ██╔██╗ ██║██║   ██║██║  ██║█████╗  
            {Fore.GREEN + Style.BRIGHT}       ██╔══██║██║  ██║██╔══██╗    ██║╚██╗██║██║   ██║██║  ██║██╔══╝  
            {Fore.GREEN + Style.BRIGHT}       ██║  ██║██████╔╝██████╔╝    ██║ ╚████║╚██████╔╝██████╔╝███████╗
            {Fore.GREEN + Style.BRIGHT}       ╚═╝  ╚═╝╚═════╝ ╚═════╝     ╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚══════╝
            {Fore.YELLOW + Style.BRIGHT}       Modified idOS Script (Two-Step Daily Check)
            """
        )

    async def load_proxies(self):
        filename = "proxy.txt"
        try:
            if not os.path.exists(filename): return
            with open(filename, 'r') as f:
                self.proxies = [line.strip() for line in f.read().splitlines() if line.strip()]
        except Exception as e:
            self.log(f"{Fore.RED}Failed To Load Proxies: {e}")

    def get_next_proxy_for_account(self, account):
        if account not in self.account_proxies:
            if not self.proxies: return None
            proxy = self.proxies[self.proxy_index]
            if not any(proxy.startswith(s) for s in ["http://", "https://", "socks4://", "socks5://"]):
                proxy = f"http://{proxy}"
            self.account_proxies[account] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[account]

    def build_proxy_config(self, proxy=None):
        if not proxy: return None, None, None
        if proxy.startswith("socks"):
            return ProxyConnector.from_url(proxy), None, None
        elif proxy.startswith("http"):
            match = re.match(r"http://(.*?):(.*?)@(.*)", proxy)
            if match:
                username, password, host_port = match.groups()
                return None, f"http://{host_port}", BasicAuth(username, password)
            return None, proxy, None
        return None, None, None

    def generate_address(self, account: str):
        try: return Account.from_key(account).address
        except: return None

    def decode_token(self, token: str):
        try:
            payload = token.split(".")[1]
            decoded_payload = urlsafe_b64decode(payload + "==").decode("utf-8")
            return json.loads(decoded_payload)["userId"]
        except: return None

    async def auth_message(self, address: str, proxy_url=None):
        url = f"{self.BASE_API}/auth/message"
        data = json.dumps({"publicAddress": address, "publicKey": address})
        headers = {**self.HEADERS[address], "Content-Type": "application/json"}
        connector, proxy, auth = self.build_proxy_config(proxy_url)
        try:
            async with ClientSession(connector=connector) as session:
                async with session.post(url, headers=headers, data=data, proxy=proxy, proxy_auth=auth) as res:
                    return await res.json()
        except: return None

    async def auth_verify(self, account, address, auth_msg, proxy_url=None):
        url = f"{self.BASE_API}/auth/verify"
        message = auth_msg.get("message")
        nonce = auth_msg.get("nonce")
        signed_message = Account.sign_message(encode_defunct(text=message), private_key=account)
        payload = {
            "publicAddress": address, "publicKey": address,
            "signature": to_hex(signed_message.signature),
            "message": message, "nonce": nonce, "walletType": "evm"
        }
        headers = {**self.HEADERS[address], "Content-Type": "application/json"}
        connector, proxy, auth = self.build_proxy_config(proxy_url)
        try:
            async with ClientSession(connector=connector) as session:
                async with session.post(url, headers=headers, data=json.dumps(payload), proxy=proxy, proxy_auth=auth) as res:
                    return await res.json()
        except: return None

    async def user_points(self, address, proxy_url=None):
        url = f"{self.BASE_API}/user/{self.user_ids[address]}/points"
        headers = {**self.HEADERS[address], "Authorization": f"Bearer {self.access_tokens[address]}"}
        connector, proxy, auth = self.build_proxy_config(proxy_url)
        try:
            async with ClientSession(connector=connector) as session:
                async with session.get(url, headers=headers, proxy=proxy, proxy_auth=auth) as res:
                    return await res.json()
        except: return None

    # --- UPDATED DAILY CHECK FLOW (FIXED) ---
    async def daily_check(self, address, proxy_url=None):
        self.log(f"{Fore.YELLOW}Attempting Daily Check-in...{Style.RESET_ALL}")
        
        # အဆင့် ၁: Quest status ကိုအရင်စစ် (GET Request)
        check_url = f"{self.BASE_API}/user-quests/{self.user_ids[address]}"
        headers = {
            **self.HEADERS[address], 
            "Authorization": f"Bearer {self.access_tokens[address]}",
            "Referer": "https://app.idos.network/",
            "Origin": "https://app.idos.network"
        }
        connector, proxy, auth = self.build_proxy_config(proxy_url)
        
        try:
            async with ClientSession(connector=connector) as session:
                async with session.get(check_url, headers=headers, proxy=proxy, proxy_auth=auth) as check_res:
                    if check_res.status != 200:
                        self.log(f"{Fore.RED}Quest Check Failed: {check_res.status}{Style.RESET_ALL}")

                # အဆင့် ၂: Pop-up ကနေ Check-in လုပ်တဲ့အဆင့် (POST Request)
                complete_url = f"{self.BASE_API}/user-quests/complete"
                payload = {"questName": "daily_check", "userId": self.user_ids[address]}
                data = json.dumps(payload)
                
                headers["Content-Type"] = "application/json"
                headers["Content-Length"] = str(len(data))

                async with session.post(complete_url, headers=headers, data=data, proxy=proxy, proxy_auth=auth) as res:
                    res_data = await res.json()
                    if res.status == 200:
                        self.log(f"{Fore.GREEN}Check-In: Claimed Successfully!{Style.RESET_ALL}")
                        return True
                    else:
                        # Claim ပြီးသားဆိုရင် status 400 ဒါမှမဟုတ် message ပါလာမယ်
                        msg = res_data.get('message', 'Already Claimed or Not Available')
                        self.log(f"{Fore.YELLOW}Check-In: {msg}{Style.RESET_ALL}")
                        return False
        except Exception as e:
            self.log(f"{Fore.RED}Check-In Error: {str(e)}{Style.RESET_ALL}")
            return False

    async def process_accounts(self, account, address, use_proxy):
        proxy = self.get_next_proxy_for_account(address) if use_proxy else None
        
        auth_msg = await self.auth_message(address, proxy)
        if not auth_msg: return
        
        verify = await self.auth_verify(account, address, auth_msg, proxy)
        if not verify or "accessToken" not in verify: return

        self.access_tokens[address] = verify.get("accessToken")
        self.user_ids[address] = self.decode_token(self.access_tokens[address])
        self.log(f"{Fore.GREEN}Login Success{Style.RESET_ALL}")

        points = await self.user_points(address, proxy)
        if points: self.log(f"{Fore.CYAN}Balance : {Fore.WHITE}{points.get('totalPoints')} PTS")

        # ဒီနေရာမှာ daily_check ကို ခေါ်ထားပါတယ်
        await self.daily_check(address, proxy)

    async def main(self):
        try:
            with open('accounts.txt', 'r') as f: accounts = [l.strip() for l in f if l.strip()]
            print("1. Run With Proxy\n2. Run Without Proxy")
            choice = int(input("Choose [1/2] -> "))
            use_proxy = choice == 1
            if use_proxy: await self.load_proxies()

            while True:
                self.clear_terminal(); self.welcome()
                for acc in accounts:
                    addr = self.generate_address(acc)
                    if not addr: continue
                    print(f"{Fore.CYAN}{'='*20}[ {addr[:6]}...{addr[-6:]} ]{'='*20}")
                    self.HEADERS[addr] = {"User-Agent": FakeUserAgent().random}
                    await self.process_accounts(acc, addr, use_proxy)

                self.log("All accounts processed. Sleeping for 12 hours...")
                await asyncio.sleep(12 * 3600)
        except Exception as e: self.log(f"{Fore.RED}Error: {e}")

if __name__ == "__main__":
    asyncio.run(idOS().main())
