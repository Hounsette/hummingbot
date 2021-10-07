from decimal import Decimal
from hummingbot.client.config.config_var import ConfigVar
from hummingbot.client.settings import required_exchanges
from scalecodec.base import ScaleType, RuntimeConfigurationObject
from scalecodec.type_registry import load_type_registry_file, load_type_registry_preset


CENTRALIZED = False
EXAMPLE_PAIR = "LUNA-UST"
DEFAULT_FEES = [0., 0.]


KEYS = {
    "polkadex_wallet_address":
        ConfigVar(key="polkadex_wallet_address",
                  prompt="Enter your Polkadex wallet address >>> ",
                  required_if=lambda: "terra" in required_exchanges,
                  is_secure=True,
                  is_connect_key=True),
    "polkadex_wallet_seeds":
        ConfigVar(key="polkadex_wallet_seeds",
                  prompt="Enter your Polkadex wallet seeds >>> ",
                  required_if=lambda: "polkadex" in required_exchanges,
                  is_secure=True,
                  is_connect_key=True),
}


class Polkadexhelper:

    def __init__(self, polkadex_wallet_address: str, polkadex_wallet_seeds: str):
        runtime_config = RuntimeConfigurationObject(ss58_format=42)
        runtime_config.update_type_registry(load_type_registry_preset("default"))
        runtime_config.update_type_registry(load_type_registry_file("polkadex_types.json"))
        self.runtimeconfig = runtime_config
        self.nonce = 0
        self.polkadex_wallet_address = polkadex_wallet_address
        self.polkadex_wallet_seeds = polkadex_wallet_seeds

    def generate_Trustedcall_encoded(self, call) -> ScaleType:

        data = self.runtimeconfig.create_scale_object("TrustedCall")
        data = data.encode(call)

        return data

    def generate_JSONRPC_placeorder(self, is_buy: bool, base: str, quote: str, markettype: str, amount: Decimal, price=0):

        side = "BID" if is_buy else "ASK"
        orderprice = None if price == 0 else price
        market_type = [115, 112, 111, 116] if markettype == "SPOT" else [116, 114, 117, 115, 116, 101, 100]

        order = {
            "user_uid": self.polkadex_wallet_address,
            "market_id": {"base": base, "quote": quote},
            "market_type": market_type,
            "order_type": "LIMIT",
            "side": side,
            "quantity": amount,
            "price": orderprice,
        }

        call = {"place_order": (self.polkadex_wallet_address, order, None)}
        callencoded = self.generate_Trustedcall_encoded(call)

        print(callencoded)
