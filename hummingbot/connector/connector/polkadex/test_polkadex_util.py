from polkadex_utils import Polkadexhelper
import websockets
import asyncio
import json


async def test_create_order() -> None:
    uri = "ws://openfinex.polkadex.trade:8020"
    seed = "//Alice"
    mrenclave = "GioSfR83Gj7eMkvPdWzKaDqgw4McPTmiXM8yLhPLAupH"
    shardhash = mrenclave
    plk = Polkadexhelper(seed, mrenclave, shardhash)
    rpc = plk.generate_JSONRPC_placeorder(True, "BTC", "USD", "SPOT", 100, 1.0)
    print(rpc)
    async with websockets.connect(uri) as cli:
        print("Sending============>")
        msg = await cli.send(json.dumps(rpc))
        print("Receiving<============")
        msg: str = await cli.recv()
        print(msg)
        msgjson = json.loads(msg)
        decodedmsg = plk.decode_RpcResult(bytearray(msgjson["result"]))
        print("Decoded message : " + str(decodedmsg))


async def test_get_balance() -> None:
    uri = "ws://openfinex.polkadex.trade:8020"
    seed = "//Alice"
    mrenclave = "GioSfR83Gj7eMkvPdWzKaDqgw4McPTmiXM8yLhPLAupH"
    shardhash = mrenclave
    plk = Polkadexhelper(seed, mrenclave, shardhash)
    rpc = plk.generate_JSONRPC_getbalance("BTC")
    print(rpc)
    async with websockets.connect(uri) as cli:
        print("Sending============>")
        msg = await cli.send(json.dumps(rpc))
        print("Receiving<============")
        msg: str = await cli.recv()
        print(msg)
        msgjson = json.loads(msg)
        decodedmsg = plk.decode_RpcResult(bytearray(msgjson["result"]))
        print("Decoded message : " + str(decodedmsg))
        balancedecoded = plk.decode_balance(decodedmsg["value"])
        print(balancedecoded)


async def test_cancel_order() -> None:
    uri = "ws://openfinex.polkadex.trade:8020"
    seed = "//Alice"
    mrenclave = "GioSfR83Gj7eMkvPdWzKaDqgw4McPTmiXM8yLhPLAupH"
    shardhash = mrenclave
    plk = Polkadexhelper(seed, mrenclave, shardhash)
    rpc = plk.generate_JSONRPC_cancelorder("ec41bdeb-2509-11ec-8294-0242ac160007", "BTC", "USD")
    print(rpc)
    async with websockets.connect(uri) as cli:
        print("Sending============>")
        msg = await cli.send(json.dumps(rpc))
        print("Receiving<============")
        msg: str = await cli.recv()
        print(msg)


def main() -> None:
    asyncio.get_event_loop().run_until_complete(test_create_order())
    asyncio.get_event_loop().run_until_complete(test_cancel_order())
    asyncio.get_event_loop().run_until_complete(test_get_balance())


if __name__ == '__main__':
    main()
