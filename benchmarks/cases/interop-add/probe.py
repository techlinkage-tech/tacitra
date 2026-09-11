import json
import subprocess
import sys


request = {"jsonrpc": "2.0", "id": 1, "method": "add", "params": {"left": 20, "right": 22}}
worker = subprocess.run(
    sys.argv[1:], input=json.dumps(request) + "\n", text=True, capture_output=True, check=True
)
response = json.loads(worker.stdout)
print(response["result"])
