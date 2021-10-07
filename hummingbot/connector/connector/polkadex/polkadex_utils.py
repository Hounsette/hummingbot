from decimal import Decimal
from hummingbot.client.config.config_var import ConfigVar
from hummingbot.client.settings import required_exchanges
from scalecodec.base import ScaleType, RuntimeConfigurationObject, ScaleBytes
from scalecodec.type_registry import load_type_registry_file, load_type_registry_preset
from substrateinterface import Keypair
import base58

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

    def __init__(self, polkadex_wallet_address: str, polkadex_wallet_seeds: str, mrenclavehash: str, shardhash: str):
        runtime_config = RuntimeConfigurationObject(ss58_format=42)
        runtime_config.update_type_registry(load_type_registry_preset("default"))
        runtime_config.update_type_registry(load_type_registry_file("polkadex_types.json"))
        self.runtimeconfig = runtime_config
        self.nonce = 0
        self.polkadex_wallet_address = polkadex_wallet_address
        self.polkadex_wallet_seeds = polkadex_wallet_seeds
        self.mrenclavehash = mrenclavehash
        self.shardhash = shardhash

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

        """ generate keypair from seed """
        if self.polkadex_wallet_seeds[0] == "/":       # only for test purposes
            keypair = Keypair.create_from_uri(self.polkadex_wallet_seeds)
        else:
            keypair = Keypair.create_from_mnemonic(self.polkadex_wallet_seeds)

        trustedcallsigned = self.sign_Trustedcall(callencoded, call, keypair)
        trustedoperationencoded = self.generate_TrustedOperation_encoded(trustedcallsigned)

        directrequest = self.generate_DirectRequest(trustedoperationencoded)
        request = {
            "jsonrpc": "2.0",
            "method": "place_order",
            "params": list(directrequest),
            "id": 1
        }

        return request

    def sign_Trustedcall(self, trustedcallencoded, trustedcall, keypair) -> dict:

        mrenclave = "0x" + base58.b58decode(self.mrenclavehash).hex()
        shard = "0x" + base58.b58decode(self.shardhash).hex()

        nonceencoded = self.runtimeconfig.create_scale_object("U32")
        nonceencoded = nonceencoded.encode(self.nonce)

        mrenclaveencoded = self.runtimeconfig.create_scale_object("H256")
        mrenclaveencoded = mrenclaveencoded.encode(mrenclave)

        shardencoded = self.runtimeconfig.create_scale_object("H256")
        shardencoded = shardencoded.encode(shard)

        payload = trustedcallencoded.data + nonceencoded.data + mrenclaveencoded.data + shardencoded.data
        signature = keypair.sign(payload.hex())
        trustedcallsigned = {
            "call": trustedcall,
            "nonce": self.nonce,
            "signature": signature
        }
        return trustedcallsigned

    def generate_TrustedOperation_encoded(self, trustedcallsigned) -> ScaleBytes:
        data = self.runtimeconfig.create_scale_object("TrustedOperation")
        trustedoperation = data.encode({"direct_call": trustedcallsigned})
        return trustedoperation

    def generate_DirectRequest(self, trustedoperationencoded) -> bytearray:
        data = self.runtimeconfig.create_scale_object("DirectRequest")
        shard = "0x" + base58.b58decode(self.shardhash).hex()
        directrequest = data.encode({
            "shard": shard,
            "encoded_text": list(trustedoperationencoded.data)})
        return directrequest.data
