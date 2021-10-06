from hummingbot.client.config.config_var import ConfigVar
from hummingbot.client.settings import required_exchanges
from scalecodec.base import RuntimeConfigurationObject
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

    def __init__(self):
        runtime_config = RuntimeConfigurationObject(ss58_format=42)
        runtime_config.update_type_registry(load_type_registry_preset("default"))
        runtime_config.update_type_registry(load_type_registry_file("polkadex_types.json"))
        self.runtimeconfig = runtime_config
