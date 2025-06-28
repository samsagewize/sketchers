import os
import json
import logging
from flask import Flask, render_template, request, send_from_directory
from web3 import Web3
from web3.exceptions import Web3Exception

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── CONFIG ─────────────────────────────────────────────────────
IMAGE_SIZE = (790, 875)
STATIC_PATH = 'static'
JSONS_PATH = os.path.join(STATIC_PATH, 'jsons')
LAYER_ORDER = [
    'background', 'accessories2', 'bodies', 'eyes', 'mouth',
    'shirts', 'hairs', 'earrings', 'toys', 'accessories', 'health'
]

# Map JSON trait_types to LAYER_ORDER
TRAIT_TO_LAYER = {
    'background': 'background',
    'accessories2': 'accessories2',
    'bodies': 'bodies',
    'eyes': 'eyes',
    'mouth': 'mouth',
    'shirts': 'shirts',
    'hairs': 'hairs',
    'earrings': 'earrings',
    'toys': 'toys',
    'accessories': 'accessories',
    'health': 'health',
    'hair2': 'hairs',
    'niqab': None,
    'glasses': None,
    'hats': None,
    'heads': None
}

IPFS_GATEWAY = "https://gateway.lighthouse.storage/ipfs/"

RPC_URL = os.getenv("RPC_URL", "https://api.mainnet.abs.xyz")
w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    logger.warning("Could not connect to RPC. Web3 features disabled.")
    w3 = None

CONTRACT_ADDRESS = Web3.to_checksum_address("0x08533A2b16e3db03eeBD5b23210122f97dfcb97d")
TRANSFER_SIG = w3.keccak(text="Transfer(address,address,uint256)").hex() if w3 else None
CONS_SIG = w3.keccak(text="ConsecutiveTransfer(uint256,uint256,address,address)").hex() if w3 else None

ERC721_ENUM_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
     "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_index", "type": "uint256"}],
     "name": "tokenOfOwnerByIndex", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
]

# ─── WEB3 FUNCTIONS ─────────────────────────────────────────────
def fetch_via_enumeration(c_addr, owner):
    if w3 is None:
        return []
    c = w3.eth.contract(address=c_addr, abi=ERC721_ENUM_ABI)
    bal = c.functions.balanceOf(owner).call()
    return [c.functions.tokenOfOwnerByIndex(owner, i).call() for i in range(bal)]

def fetch_via_logs(c_addr, owner, start_block=0, chunk=50_000):
    if w3 is None:
        return []
    owner_lc = owner.lower()
    latest = w3.eth.block_number
    myset = set()
    for frm in range(max(latest - 100_000, start_block), latest + 1, chunk):
        to = min(frm + chunk - 1, latest)
        try:
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
        except Exception as e:
            logger.warning(f"Log fetch failed for block {frm}-{to}: {e}")
    return sorted(myset)

def fetch_my_tokens(c_addr, owner):
    try:
        return fetch_via_enumeration(c_addr, owner)
    except Exception as e:
        logger.warning(f"Enumeration failed: {e}")
        return fetch_via_logs(c_addr, owner)

# ─── JSON LOADING FUNCTION ─────────────────────────────────────
def load_token_metadata(token_ids):
    metadata = {}
    for token_id in token_ids:
        file_path = os.path.join(JSONS_PATH, str(token_id))
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                traits = {}
                for attr in data.get('attributes', []):
                    layer = TRAIT_TO_LAYER.get(attr['trait_type'])
                    if layer:
                        traits[layer] = attr['value'] if attr['value'] != 'None' else None
                image_url = data.get('image', '')
                if image_url.startswith('ipfs://'):
                    image_url = IPFS_GATEWAY + image_url.replace('ipfs://', '')
                metadata[str(token_id)] = {
                    'name': data.get('name'),
                    'image': image_url,
                    'traits': traits
                }
        except FileNotFoundError:
            logger.warning(f"Metadata file {file_path} not found")
            metadata[str(token_id)] = {'error': f"Metadata for token {token_id} not found"}
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in {file_path}")
            metadata[str(token_id)] = {'error': f"Invalid JSON for token {token_id}"}
    return metadata

# ─── ROUTES ─────────────────────────────────────────────────────
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

@app.route('/redeem', methods=["GET", "POST"])
def redeem():
    try:
        layer_files = {}
        for layer in LAYER_ORDER:
            folder = os.path.join(STATIC_PATH, layer)
            try:
                files = sorted(f for f in os.listdir(folder) if f.lower().endswith('.png'))
            except FileNotFoundError:
                logger.warning(f"Directory {folder} not found")
                files = []
            layer_files[layer] = files

        error = None
        user_toks = []
        metadata = {}
        if request.method == "POST":
            raw_o = request.form.get("owner", "").strip()
            try:
                o = Web3.to_checksum_address(raw_o)
                user_toks = fetch_my_tokens(CONTRACT_ADDRESS, o)
                metadata = load_token_metadata(user_toks)
            except Exception as e:
                error = f"🚨 {e}"
                logger.error(f"Web3 error: {e}")

        return render_template(
            'redeem.html',
            layers=LAYER_ORDER,
            layer_files=layer_files,
            image_size=IMAGE_SIZE,
            error=error,
            user_toks=user_toks,
            metadata=metadata
        )
    except Exception as e:
        logger.error(f"Unexpected error in /redeem: {e}")
        return render_template('error.html', error="Internal server error. Please try again later."), 500

@app.route('/static/<path:path>')
def static_proxy(path):
    return send_from_directory(STATIC_PATH, path)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')