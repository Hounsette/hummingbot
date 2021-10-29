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

    def __init__(self, polkadex_wallet_seeds: str, mrenclavehash: str, shardhash: str):
        runtime_config = RuntimeConfigurationObject(ss58_format=42)
        runtime_config.update_type_registry(load_type_registry_preset("default"))
        runtime_config.update_type_registry(load_type_registry_file("polkadex_types.json"))
        self.runtimeconfig = runtime_config
        self.nonce = 0
        self.polkadex_wallet_seeds = polkadex_wallet_seeds
        self.mrenclavehash = mrenclavehash
        self.shardhash = shardhash
        """ generate keypair from seed """
        if self.polkadex_wallet_seeds[0] == "/":       # only for test purposes
            keypair = Keypair.create_from_uri(self.polkadex_wallet_seeds)
        else:
            keypair = Keypair.create_from_mnemonic(self.polkadex_wallet_seeds)
        self.keypair = keypair

    def generate_Trustedcall_encoded(self, call) -> ScaleType:

        data = self.runtimeconfig.create_scale_object("TrustedCall")
        data = data.encode(call)

        return data

    def generate_TrustedGetter_encoded(self, call) -> ScaleType:

        data = self.runtimeconfig.create_scale_object("TrustedGetter")
        data = data.encode(call)

        return data

    def generate_JSONRPC_placeorder(self, is_buy: bool, base: str, quote: str, markettype: str, amount: Decimal, price=0):

        side = "BID" if is_buy else "ASK"
        orderprice = None if price == 0 else price
        market_type = [115, 112, 111, 116] if markettype == "SPOT" else [116, 114, 117, 115, 116, 101, 100]

        order = {
            "user_uid": self.keypair.public_key,
            "market_id": {"base": base, "quote": quote},
            "market_type": market_type,
            "order_type": "LIMIT",
            "side": side,
            "quantity": amount,
            "price": orderprice,
        }
        call = {"place_order": (self.keypair.public_key, order, None)}
        callencoded = self.generate_Trustedcall_encoded(call)

        trustedcallsigned = self.sign_Trustedcall(callencoded, call)
        trustedoperationencoded = self.generate_TrustedOperation_encoded(trustedcallsigned, "direct_call")

        directrequest = self.generate_DirectRequest(trustedoperationencoded)
        request = {
            "jsonrpc": "2.0",
            "method": "place_order",
            "params": list(directrequest),
            "id": 1
        }

        return request

    def generate_JSONRPC_cancelorder(self, uuid: str, base: str, quote: str):

        data = self.runtimeconfig.create_scale_object("Vec<u8>")
        uuidencoded = data.encode(uuid)

        order = {
            "user_uid": self.keypair.public_key,
            "market_id": {"base": base, "quote": quote},
            "order_id": list(uuidencoded.data)
        }
        call = {"cancel_order": (self.keypair.public_key, order, None)}
        callencoded = self.generate_Trustedcall_encoded(call)

        trustedcallsigned = self.sign_Trustedcall(callencoded, call)
        trustedoperationencoded = self.generate_TrustedOperation_encoded(trustedcallsigned, "direct_call")

        directrequest = self.generate_DirectRequest(trustedoperationencoded)
        request = {
            "jsonrpc": "2.0",
            "method": "cancel_order",
            "params": list(directrequest),
            "id": 1
        }

        return request

    def generate_JSONRPC_getbalance(self, currencyId: str):

        call = {"get_balance": (self.keypair.public_key, currencyId, None)}
        callencoded = self.generate_TrustedGetter_encoded(call)

        trustedGetterSigned = self.sign_TrustedGetter(callencoded, call)
        getter = {"trusted": trustedGetterSigned}
        trustedoperationencoded = self.generate_TrustedOperation_encoded(getter, "get")

        directrequest = self.generate_DirectRequest(trustedoperationencoded)
        request = {
            "jsonrpc": "2.0",
            "method": "get_balance",
            "params": list(directrequest),
            "id": 1
        }

        return request

    def sign_TrustedGetter(self, trustedcallencoded, trustedcall) -> dict:

        payload = trustedcallencoded

        signature = self.keypair.sign(payload)

        signatureSr25519 = {"Sr25519": signature}

        trustedGettersigned = {
            "getter": trustedcall,
            "signature": signatureSr25519
        }
        return trustedGettersigned

    def sign_Trustedcall(self, trustedcallencoded, trustedcall) -> dict:

        mrenclave = "0x" + base58.b58decode(self.mrenclavehash).hex()
        shard = "0x" + base58.b58decode(self.shardhash).hex()

        nonceencoded = self.runtimeconfig.create_scale_object("U32")
        nonceencoded = nonceencoded.encode(self.nonce)

        mrenclaveencoded = self.runtimeconfig.create_scale_object("H256")
        mrenclaveencoded = mrenclaveencoded.encode(mrenclave)

        shardencoded = self.runtimeconfig.create_scale_object("H256")
        shardencoded = shardencoded.encode(shard)

        payload = trustedcallencoded + nonceencoded + mrenclaveencoded + shardencoded

        signature = self.keypair.sign(payload)

        signatureSr25519 = {"Sr25519": signature}

        trustedcallsigned = {
            "call": trustedcall,
            "nonce": self.nonce,
            "signature": signatureSr25519
        }
        return trustedcallsigned

    def generate_TrustedOperation_encoded(self, trustedcallsigned, typeofcall: str) -> ScaleBytes:
        data = self.runtimeconfig.create_scale_object("TrustedOperation")
        trustedoperation = data.encode({typeofcall: trustedcallsigned})
        return trustedoperation

    def generate_DirectRequest(self, trustedoperationencoded) -> bytearray:
        data = self.runtimeconfig.create_scale_object("DirectRequest")
        shard = "0x" + base58.b58decode(self.shardhash).hex()
        directrequest = data.encode({
            "shard": shard,
            "encoded_text": trustedoperationencoded.data})
        return directrequest.data

    def decode_RpcResult(self, data: bytearray) -> dict:
        returndata = self.runtimeconfig.create_scale_object("RpcReturnValue", ScaleBytes(data))
        returndata = returndata.decode()
        return returndata

    def decode_balance(self, data) -> dict:
        returndata = self.runtimeconfig.create_scale_object("Balances", ScaleBytes(data))
        returndata = returndata.decode()
        return returndata
