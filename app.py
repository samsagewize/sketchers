import os
import json
from flask import Flask, render_template, send_from_directory, request
from web3 import Web3

app = Flask(__name__)

# ─── CONFIG ─────────────────────────────────────────────────────
IMAGE_SIZE = (790, 875)
STATIC_PATH = 'static'
LAYER_ORDER = [
    'background',
    'accessories2',  # ← new behind bodies, in front of background
    'bodies',
    'eyes',
    'mouth',
    'shirts',
    'hairs',
    'earrings',
    'toys',
    'accessories',
    'health',  # ← overlays everything at 30% opacity
]

# Web3 Configuration for /redeempoints
RPC_URL = os.getenv("RPC_URL", "https://api.mainnet.abs.xyz")
w3 = None
try:
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print("Warning: Could not connect to Abstract RPC")
        w3 = None
except Exception as e:
    print(f"Warning: Web3 initialization failed: {e}")
    w3 = None

# Your SketchyMilio contract
CONTRACT_ADDRESS = (
    Web3.to_checksum_address("0x08533A2b16e3db03eeBD5b23210122f97dfcb97d")
    if w3
    else None
)

# Event signatures
TRANSFER_SIG = w3.keccak(text="Transfer(address,address,uint256)").hex() if w3 else None
CONS_SIG = w3.keccak(text="ConsecutiveTransfer(uint256,uint256,address,address)").hex() if w3 else None

# Minimal ERC-721 Enumerable ABI
ERC721_ENUM_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_index", "type": "uint256"},
        ],
        "name": "tokenOfOwnerByIndex",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
]

def fetch_via_enumeration(c_addr, owner):
    if not w3:
        return []
    c = w3.eth.contract(address=c_addr, abi=ERC721_ENUM_ABI)
    bal = c.functions.balanceOf(owner).call()
    return [c.functions.tokenOfOwnerByIndex(owner, i).call() for i in range(bal)]

def fetch_via_logs(c_addr, owner, start_block=0, chunk=200_000):
    if not w3:
        return []
    owner_lc = owner.lower()
    latest = w3.eth.block_number
    myset = set()

    for frm in range(start_block, latest + 1, chunk):
        to = min(frm + chunk - 1, latest)
        logs = w3.eth.get_logs({
            "fromBlock": frm,
            "toBlock": to,
            "address": c_addr,
            "topics": [None],
        })

        for ev in logs:
            sig = ev["topics"][0].hex()
            # Single transfers
            if sig == TRANSFER_SIG:
                frm_a = "0x" + ev["topics"][1].hex()[-40:]
                to_a = "0x" + ev["topics"][2].hex()[-40:]
                tid = int.from_bytes(ev["topics"][3], "big")
                if to_a.lower() == owner_lc:
                    myset.add(tid)
                if frm_a.lower() == owner_lc:
                    myset.discard(tid)
            # Batch mints
            elif sig == CONS_SIG:
                ft = int(ev["topics"][1].hex(), 16)
                tt = int(ev["topics"][2].hex(), 16)
                fa = "0x" + ev["topics"][3].hex()[-40:]
                ta = "0x" + ev["data"].hex()[-40:]
                if ta.lower() == owner_lc:
                    myset.update(range(ft, tt + 1))
                if fa.lower() == owner_lc:
                    for x in range(ft, tt + 1):
                        myset.discard(x)

    return sorted(myset)

def fetch_my_tokens(c_addr, owner):
    if not w3 or not c_addr:
        return []
    try:
        return fetch_via_enumeration(c_addr, owner)
    except Exception:
        return fetch_via_logs(c_addr, owner)

# ─── ROUTES ─────────────────────────────────────────────────────

@app.route('/')
def index():
    # Gather PNGs per layer
    layer_files = {}
    for layer in LAYER_ORDER:
        folder = os.path.join(STATIC_PATH, layer)
        try:
            files = sorted(f for f in os.listdir(folder) if f.lower().endswith('.png'))
        except FileNotFoundError:
            files = []
        layer_files[layer] = files

    return render_template(
        'index.html',
        layers=LAYER_ORDER,
        layer_files=layer_files,
        image_size=IMAGE_SIZE
    )

@app.route('/traits')
def traits():
    # Load report.json from the static folder
    report_path = os.path.join(STATIC_PATH, 'report.json')
    try:
        with open(report_path, 'r') as f:
            report_data = json.load(f)
    except FileNotFoundError:
        report_data = {"traits": {}, "error": "report.json not found"}
    except json.JSONDecodeError:
        report_data = {"traits": {}, "error": "Invalid JSON in report.json"}

    return render_template(
        'test.html',
        report=report_data
    )

@app.route('/redeempoints', methods=['GET', 'POST'])
def redeempoints():
    error = None
    user_toks = None

    if not w3:
        error = "🚨 Blockchain connection is not available. Please try again later."

    if request.method == 'POST' and w3:
        raw_o = request.form.get('owner', '').strip()
        try:
            o = Web3.to_checksum_address(raw_o)
            user_toks = fetch_my_tokens(CONTRACT_ADDRESS, o)
        except Exception as e:
            error = f"🚨 Invalid wallet address or error: {e}"

    return render_template(
        'redeempoints.html',
        error=error,
        user_toks=user_toks
    )

# Serve static files
@app.route('/static/<path:path>')
def static_proxy(path):
    return send_from_directory(STATIC_PATH, path)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')