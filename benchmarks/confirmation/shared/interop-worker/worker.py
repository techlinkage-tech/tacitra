import json
import sys


def dispatch(method, values):
    if method == "add":
        return values["left"] + values["right"]
    if method == "subtract":
        return values["left"] - values["right"]
    if method == "multiply":
        return values["left"] * values["right"]
    if method == "affine":
        return values["value"] * values["factor"] + values["offset"]
    raise KeyError(method)


request = json.loads(sys.stdin.readline())
response = {"jsonrpc": "2.0", "id": request["id"], "result": dispatch(request["method"], request["params"]), "meta": {"effects": [], "capabilities": []}}
print(json.dumps(response, separators=(",", ":"), sort_keys=True))
