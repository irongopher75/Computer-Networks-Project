from flask import Flask, jsonify, request, send_from_directory, Response
from pathlib import Path


app = Flask(__name__, static_folder=str(Path(__file__).parent))


def xor(a: str, b: str) -> str:
    result_bits = []
    for i in range(1, len(b)):
        result_bits.append('0' if a[i] == b[i] else '1')
    return ''.join(result_bits)


def mod2div(dividend: str, divisor: str) -> str:
    pick = len(divisor)
    tmp = dividend[0: pick]
    while pick < len(dividend):
        if tmp[0] == '1':
            tmp = xor(divisor, tmp) + dividend[pick]
        else:
            tmp = xor('0' * pick, tmp) + dividend[pick]
        pick += 1
    if tmp[0] == '1':
        tmp = xor(divisor, tmp)
    else:
        tmp = xor('0' * pick, tmp)
    return tmp


def encode_data(data: str, key: str):
    appended = data + '0' * (len(key) - 1)
    remainder = mod2div(appended, key)
    codeword = data + remainder
    return appended, remainder, codeword


def _is_bits(s: str) -> bool:
    return isinstance(s, str) and len(s) > 0 and all(c in '01' for c in s)


# ----------------- Hamming (SEC) -----------------
def calc_parity_bits_len(m: int) -> int:
    r = 0
    while (2 ** r) < (m + r + 1):
        r += 1
    return r


def place_redundant_bits(data: str, r: int) -> str:
    j = 0
    k = 1
    m = len(data)
    res = ''
    for i in range(1, m + r + 1):
        if i == (2 ** j):
            res = res + '0'
            j += 1
        else:
            res = res + data[-1 * k]
            k += 1
    return res[::-1]


def calc_parity_values(arr: str, r: int) -> str:
    n = len(arr)
    arr_list = list(arr)
    for i in range(r):
        val = 0
        for j in range(1, n + 1):
            if j & (2 ** i) == (2 ** i):
                val = val ^ int(arr_list[-1 * j])
        arr_list[n - (2 ** i)] = str(val)
    return ''.join(arr_list)


def detect_hamming_error(arr: str, r: int) -> int:
    n = len(arr)
    res = 0
    for i in range(r):
        val = 0
        for j in range(1, n + 1):
            if j & (2 ** i) == (2 ** i):
                val = val ^ int(arr[-1 * j])
        res += val * (2 ** i)
    return res


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "home.html")

@app.get("/crc")
def crc_page():
    return send_from_directory(app.static_folder, "crc.html")

@app.get("/hamming")
def hamming_page():
    return send_from_directory(app.static_folder, "hamming.html")

@app.get('/favicon.ico')
def favicon():
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
        "<rect width='64' height='64' rx='8' fill='#111827'/>"
        "<path d='M10 34h44' stroke='#22c55e' stroke-width='6'/>"
        "<circle cx='20' cy='24' r='4' fill='#e5e7eb'/><circle cx='44' cy='44' r='4' fill='#e5e7eb'/>"
        "</svg>"
    )
    return Response(svg, mimetype='image/svg+xml')

@app.post("/api/encode")
def api_encode():
    payload = request.get_json(silent=True) or {}
    data = (payload.get("data") or "").strip()
    key = (payload.get("key") or "").strip()
    if not _is_bits(data) or not _is_bits(key) or not key.startswith('1'):
        return jsonify({"error": "Invalid data or key"}), 400
    appended, remainder, codeword = encode_data(data, key)
    return jsonify({
        "appended": appended,
        "remainder": remainder,
        "codeword": codeword,
    })


@app.post("/api/check")
def api_check():
    payload = request.get_json(silent=True) or {}
    received = (payload.get("received") or "").strip()
    key = (payload.get("key") or "").strip()
    if not _is_bits(received) or not _is_bits(key) or not key.startswith('1'):
        return jsonify({"error": "Invalid received or key"}), 400
    syndrome = mod2div(received, key)
    ok = ('1' not in syndrome)
    return jsonify({
        "syndrome": syndrome,
        "ok": ok,
    })


@app.post("/api/hamming/encode")
def api_hamming_encode():
    payload = request.get_json(silent=True) or {}
    data = (payload.get("data") or "").strip()
    if not _is_bits(data):
        return jsonify({"error": "Invalid data"}), 400
    m = len(data)
    r = calc_parity_bits_len(m)
    arr = place_redundant_bits(data, r)
    code = calc_parity_values(arr, r)
    return jsonify({
        "r": r,
        "codeword": code,
    })


@app.post("/api/hamming/check")
def api_hamming_check():
    payload = request.get_json(silent=True) or {}
    received = (payload.get("received") or "").strip()
    r = payload.get("r")
    if not _is_bits(received) or not isinstance(r, int) or r < 0:
        return jsonify({"error": "Invalid received or r"}), 400
    pos = detect_hamming_error(received, r)
    ok = (pos == 0)
    corrected = None
    if not ok and 1 <= pos <= len(received):
        idx = len(received) - pos
        rl = list(received)
        rl[idx] = '1' if rl[idx] == '0' else '0'
        corrected = ''.join(rl)
    return jsonify({
        "ok": ok,
        "error_position": pos,
        "corrected": corrected,
    })


if __name__ == "__main__":
    # Run dev server
    app.run(host="127.0.0.1", port=5000, debug=True)


