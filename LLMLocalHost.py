import llmgraphbuilder
import socket
from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import random

def get_local_ip():
    """Find the local network IP of this machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't have to be reachable, just used for finding IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

app = Flask(__name__)

@app.route("/run", methods=["POST"])
def run():
    data = request.json
    result = llmgraphbuilder.prompt(data)
    return jsonify({"result": result})
    #c=random.randint(0,2000)
    #return jsonify("Babbaboi" + str(data))

if __name__ == "__main__":
    local_ip = get_local_ip()
    print(f"Server running at: http://{local_ip}:5000/run")
    app.run(host="0.0.0.0", port=5000)
