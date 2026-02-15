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
        self.refresh_tokens = {}

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
            {Fore.YELLOW + Style.BRIGHT}       Modified for New idOS API Flow
            """
        )

    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    
    async def load_proxies(self):
        filename = "proxy.txt"
        try:
            if not os.path.exists(filename):
                self.log(f"{Fore.RED + Style.BRIGHT}File {filename} Not Found.{Style.RESET_ALL}")
                return
            with open(filename, 'r') as f:
                self.proxies = [line.strip() for line in f.read().splitlines() if line.strip()]
            
            if not self.proxies:
                self.log(f"{Fore.RED + Style.BRIGHT}No Proxies Found.{Style.RESET_ALL}")
                return

            self.log(
                f"{Fore.GREEN + Style.BRIGHT}Proxies Total  : {Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT}{len(self.proxies)}{Style.RESET_ALL}"
            )
        
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Failed To Load Proxies: {e}{Style.RESET_ALL}")
            self.proxies = []

    def check_proxy_schemes(self, proxies):
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxies.startswith(scheme) for scheme in schemes):
            return proxies
        return f"http://{proxies}"

    def get_next_proxy_for_account(self, account):
        if account not in self.account_proxies:
            if not self.proxies:
                return None
            proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
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
        except Exception as e:
            self.log(f"{Fore.RED}Fetch User Id Failed: {str(e)}{Style.RESET_ALL}")
            return None

    def generate_payload(self, account: str, address: str, auth_message: dict):
        message = auth_message.get("message")
        nonce = auth_message.get("nonce")
        encoded_message = encode_defunct(text=message)
        signed_message = Account.sign_message(encoded_message, private_key=account)
        return {
            "publicAddress": address, "publicKey": address,
            "signature": to_hex(signed_message.signature),
            "message": message, "nonce": nonce, "walletType": "evm"
        }

    def mask_account(self, account):
        return account[:6] + '*' * 6 + account[-6:] if account else None

    async def check_connection(self, proxy_url=None):
        connector, proxy, auth = self.build_proxy_config(proxy_url)
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=20)) as session:
                async with session.get("https://api.ipify.org?format=json", proxy=proxy, proxy_auth=auth) as res:
                    return res.status == 200
        except: return False

    async def auth_message(self, address: str, proxy_url=None):
        url = f"{self.BASE_API}/auth/message"
        data = json.dumps({"publicAddress": address, "publicKey": address})
        headers = {**self.HEADERS[address], "Content-Type": "application/json"}
        connector, proxy, auth = self.build_proxy_config(proxy_url)
        try:
            async with ClientSession(connector=connector) as session:
                async with session.post(url, headers=headers, data=data, proxy=proxy, proxy_auth=auth) as res:
                    res.raise_for_status()
                    return await res.json()
        except Exception as e:
            self.log(f"{Fore.RED}Fetch Nonce Failed: {e}{Style.RESET_ALL}")
            return None

    async def auth_verify(self, account, address, auth_msg, proxy_url=None):
        url = f"{self.BASE_API}/auth/verify"
        data = json.dumps(self.generate_payload(account, address, auth_msg))
        headers = {**self.HEADERS[address], "Content-Type": "application/json"}
        connector, proxy, auth = self.build_proxy_config(proxy_url)
        try:
            async with ClientSession(connector=connector) as session:
                async with session.post(url, headers=headers, data=data, proxy=proxy, proxy_auth=auth) as res:
                    res.raise_for_status()
                    return await res.json()
        except Exception as e:
            self.log(f"{Fore.RED}Login Failed: {e}{Style.RESET_ALL}")
            return None

    async def user_points(self, address, proxy_url=None):
        url = f"{self.BASE_API}/user/{self.user_ids[address]}/points"
        headers = {**self.HEADERS[address], "Authorization": f"Bearer {self.access_tokens[address]}"}
        connector, proxy, auth = self.build_proxy_config(proxy_url)
        try:
            async with ClientSession(connector=connector) as session:
                async with session.get(url, headers=headers, proxy=proxy, proxy_auth=auth) as res:
                    return await res.json()
        except: return None

    # --- UPDATED DAILY CHECK FLOW ---
    async def daily_check(self, address, proxy_url=None):
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
                await session.get(check_url, headers=headers, proxy=proxy, proxy_auth=auth)
                # အဆင့် ၂: ပေါ်လာတဲ့ Pop-up ကို Check-in လုပ် (POST Request)
                complete_url = f"{self.BASE_API}/user-quests/complete"
                payload = {"questName": "daily_check", "userId": self.user_ids[address]}
                data = json.dumps(payload)
                
                headers["Content-Type"] = "application/json"
                headers["Content-Length"] = str(len(data))

                async with session.post(complete_url, headers=headers, data=data, proxy=proxy, proxy_auth=auth) as res:
                    if res.status == 200: return await res.json()
                    elif res.status in [400, 502]:
                        self.log(f"{Fore.YELLOW}Check-In: Already Claimed or Requirement Not Met{Style.RESET_ALL}")
        except Exception as e:
            self.log(f"{Fore.RED}Check-In Error: {str(e)}{Style.RESET_ALL}")
        return None

    async def process_accounts(self, account, address, use_proxy, rotate):
        proxy = self.get_next_proxy_for_account(address) if use_proxy else None
        if use_proxy and not await self.check_connection(proxy): return

        auth_msg = await self.auth_message(address, proxy)
        if not auth_msg: return
        
        verify = await self.auth_verify(account, address, auth_msg, proxy)
        if not verify: return

        self.access_tokens[address] = verify.get("accessToken")
        self.user_ids[address] = self.decode_token(self.access_tokens[address])
        self.log(f"{Fore.GREEN}Login Success{Style.RESET_ALL}")

        points = await self.user_points(address, proxy)
        if points: self.log(f"{Fore.CYAN}Balance : {Fore.WHITE}{points.get('totalPoints')} PTS")

        if await self.daily_check(address, proxy):
            self.log(f"{Fore.CYAN}Check-In: {Fore.GREEN}Claimed Successfully{Style.RESET_ALL}")

    async def main(self):
        try:
            with open('accounts.txt', 'r') as f: accounts = [l.strip() for l in f if l.strip()]
            print("1. Run With Proxy\n2. Run Without Proxy")
            choice = int(input("Choose [1/2] -> "))
            use_proxy = choice == 1
            if use_proxy: await self.load_proxies()

            while True:
                self.clear_terminal()
                self.welcome()
                for acc in accounts:
                    addr = self.generate_address(acc)
                    if not addr: continue
                    print(f"{Fore.CYAN}{'='*20}[ {self.mask_account(addr)} ]{'='*20}")
                    self.HEADERS[addr] = {"User-Agent": FakeUserAgent().random}
                    await self.process_accounts(acc, addr, use_proxy, True)

                self.log("All accounts processed. Sleeping for 12 hours...")
                await asyncio.sleep(12 * 3600)
        except Exception as e: self.log(f"{Fore.RED}Error: {e}")

if __name__ == "__main__":
    asyncio.run(idOS().main())
