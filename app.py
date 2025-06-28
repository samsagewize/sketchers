import os
import json
from flask import Flask, render_template, request, send_from_directory
from web3 import Web3

app = Flask(__name__, template_folder='templates', static_folder='static')

# ─── CONFIG: Gallery ─────────────────────────────────────────────────────
IMAGE_SIZE = (790, 875)
STATIC_PATH = 'static'
METADATA_PATH = os.path.join(STATIC_PATH, 'metadata')  # Path to JSON files
LAYER_ORDER = [
    'background',
    'accessories2',
    'bodies',
    'eyes',
    'mouth',
    'shirts',
    'hairs',
    'earrings',
    'toys',
    'accessories',
    'health',
]

# ─── CONFIG: Web3 ───────────────────────────────────────────────────────
RPC_URL = os.getenv("RPC_URL", "https://api.mainnet.abs.xyz")
w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    raise RuntimeError("❌ Could not connect to Abstract RPC")

CONTRACT_ADDRESS = Web3.to_checksum_address("0x08533A2b16e3db03eeBD5b23210122f97dfcb97d")
TRANSFER_SIG = w3.keccak(text="Transfer(address,address,uint256)").hex()
CONS_SIG = w3.keccak(text="ConsecutiveTransfer(uint256,uint256,address,address)").hex()

ERC721_ENUM_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
     "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_index", "type": "uint256"}],
     "name": "tokenOfOwnerByIndex", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
]

# ─── Web3 Functions ─────────────────────────────────────────────────────
def fetch_via_enumeration(c_addr, owner):
    c = w3.eth.contract(address=c_addr, abi=ERC721_ENUM_ABI)
    bal = c.functions.balanceOf(owner).call()
    return [c.functions.tokenOfOwnerByIndex(owner, i).call() for i in range(bal)]

def fetch_via_logs(c_addr, owner, start_block=0, chunk=200_000):
    owner_lc = owner.lower()
    latest = w3.eth.block_number
    myset = set()

    for frm in range(start_block, latest + 1, chunk):
        to = min(frm + chunk - 1, latest)
        logs = w3.eth.get_logs({
            "fromBlock": frm, "toBlock": to,
            "address": c_addr, "topics": [None]
        })

        for ev in logs:
            sig = ev["topics"][0].hex()
            if sig == TRANSFER_SIG:
                frm_a = "0x" + ev["topics"][1].hex()[-40:]
                to_a = "0x" + ev["topics"][2].hex()[-40:]
                tid = int.from_bytes(ev["topics"][3], "big")
                if to_a.lower() == owner_lc:
                    myset.add(tid)
                if frm_a.lower() == owner_lc:
                    myset.discard(tid)
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
    try:
        return fetch_via_enumeration(c_addr, owner)
    except Exception:
        return fetch_via_logs(c_addr, owner)

# ─── Routes: Gallery ────────────────────────────────────────────────────
@app.route('/')
def index():
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

# ─── Route: Web3 ───────────────────────────────────────────────────────
@app.route('/render', methods=['GET', 'POST'])
def render():
    error = None
    user_toks = None
    metadata = {}

    if request.method == 'POST':
        raw_o = request.form['owner'].strip()
        try:
            o = Web3.to_checksum_address(raw_o)
            user_toks = fetch_my_tokens(CONTRACT_ADDRESS, o)
            # Load metadata for each token from static/metadata/
            for token_id in user_toks:
                meta_path = os.path.join(METADATA_PATH, str(token_id))
                try:
                    with open(meta_path, 'r') as f:
                        metadata[token_id] = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    metadata[token_id] = {"error": f"Metadata for token {token_id} not found or invalid"}
        except Exception as e:
            error = f"🚨 {e}"

    return render_template(
        'render.html',
        error=error,
        user_toks=user_toks,
        metadata=metadata
    )

# ─── Static File Serving ───────────────────────────────────────────────
@app.route('/static/<path:path>')
def static_proxy(path):
    return send_from_directory(STATIC_PATH, path)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)