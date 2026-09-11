import json
import sys
import time


def dispatch(method, params):
    if method == "add":
        return params["left"] + params["right"], [], []
    if method == "sleep_ms":
        time.sleep(params["milliseconds"] / 1000)
        return params["milliseconds"], ["clock"], []
    if method == "explode":
        raise ValueError("example failure")
    raise KeyError(method)


request = json.loads(sys.stdin.readline())
try:
    result, effects, capabilities = dispatch(request["method"], request["params"])
    response = {
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": result,
        "meta": {"effects": effects, "capabilities": capabilities},
    }
except Exception as error:
    response = {
        "jsonrpc": "2.0",
        "id": request.get("id", 1),
        "error": {
            "code": -32000,
            "message": "external Python exception",
            "data": {"kind": type(error).__name__, "message": str(error)},
        },
    }
print(json.dumps(response, separators=(",", ":"), sort_keys=True))
