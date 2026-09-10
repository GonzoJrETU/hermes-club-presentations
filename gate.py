#!/usr/bin/env python3
"""PII gate for the public deck bundle.

Scans dist/*.html and fails the build if any forbidden token is present.

WHY THIS FILE CONTAINS NO WORDS: this repo is public, so a plaintext blocklist
would itself publish the very names the gate exists to keep out (household first
names, internal venture codenames, tracked clinicians). Instead the gate stores
**SHA-256 digests** of the normalized tokens and matches them against the 1- and
2-word n-grams of the page text. Tokens are normalized the same way as the page
text (lowercased, split on non-alphanumerics), so punctuation-heavy tokens — a
phone prefix, an email domain, a two-word place name — all match naturally.

This is a gate, not the scrubber. The scrubbers that rewrite content need the
tokens in plaintext to do their job, so they live outside the public repo (the
local FamilyStewardAI guide, `tools/`). A fresh clone already contains the
scrubbed decks, so the gate is what a rebuild needs.

Usage: python gate.py [dist-dir]
Exit:  0 = clean, 1 = leak found, 2 = usage error
"""
from __future__ import annotations

import glob
import hashlib
import os
import re
import sys

# sha256( normalized token ) -> number of words in the token (1 or 2)
HASHES: dict[str, int] = {
    "06ab7dac8250c35abb5049e6ac2d48a5be11ce5065156e847a6448fa36c26f58": 1,
    "0cc93a7ceb16cc156a0eab2dbfee793ccf440cab1cd1bdbc9194ca22edf4754a": 2,
    "1a0f1387bf24b283dba20e02d5629ce4b6f57d913a9ac78f0417bc0737346c3b": 2,
    "1d34b87b5b37741a0e3b20ec41d7c7f0ca1aa3dfd0d22610cfc8d6032d0a5d2b": 1,
    "22e4d7eebd7e2b7b60bb4e6791d36dc27f4f50bd4309ce2a1e7b654e81c2ced1": 1,
    "312f0f10c925bad1969f43a056ec0203818f97da7c0b71b2d0f83b84905228a4": 1,
    "3b0d1ecdb1284e4e5a881ef208696929a19d7419ed519cf080f5e94ee482437e": 2,
    "3d5c95aa66ecc74e56b4e1f0d7d6705544062dfb4b5dadb1a177c6dedb3a9a4b": 1,
    "3de8392541ace28284aca7f2724273739fcf4cf73de276a8ddd3547c0011323c": 1,
    "444b759c5264422ea582403ae2083d2447fd226a2e40795968dd740e9202cb97": 1,
    "45d652b87711a1418a509ae031b16ea3881c4d83e2757c2885ddbbdcd9b305ba": 2,
    "49df506d0b7d2da324567460a7a646c4d54c1ba0585bae6c614769de960e4a2f": 1,
    "4bbf345afa7fd6a394ac945dbee1164b584eedab793f06850eebc2b95545529e": 1,
    "4c4afffc7a881d7ab22f6ecc4fbfa4df46fb2ac3fa89c296db6dcfbd8d4a434d": 2,
    "54f59a87ddc675ba47439d98e80daac00534b0587001aa1fa48a969d9aa186c3": 2,
    "56584949957de203b0b6cb347b57e0553cb31115cc3049e9839b7fb944465a9b": 1,
    "64d399ec4b2e5e41cdc7f68847cd34425edb645238a8ba36f2af25c82194c977": 2,
    "67c888af8ad80f0232832431fb0bbb478f12740ff8b451d8d4ce0238a2d8b63a": 1,
    "6e7dde33b176a89242193a7f66264b1d250250adafaa9c1b240129490fe928a7": 2,
    "73faaed438b21a5182954c594a889ccd8622ea906bd2af98725a9aeb48e0d85e": 1,
    "745cc9f7c761ae00709dd707b9276fd9c987c1e86efebc11e5a6e0175947ab98": 1,
    "7679dda63f98cd975589588857915d0fc23dd55b6af2ea2efcd82911564c2750": 1,
    "84ef9e571add28dcf344e27eb489d351c8ab9808a352a65561499e77d84060fc": 1,
    "8835de21330ee10c46bff169d016d3e01c378bdf398e1a16746fc49170d11c9c": 2,
    "8cd626bd979d05205337b47dc6a80edf6372b902e3dd1d10bc99dc3ecfd38f9e": 1,
    "90f1adb96d94e0fcc5a619e01bced753809a841cb9c6c5707d3d6cb447b40eba": 1,
    "922aa67c5b92facffe7019c2a809bf925b4dc375f2a739956c85ea83322fb3a0": 1,
    "9332fe2803bf830768b3428b0db0fcb8cb4f7913938f187d55f2b4dc5813dc17": 2,
    "99423a107506bc41876b3a1b91f3782eb4426db69974dd848925b4a5d9487827": 2,
    "9abd454e2248c5a4ed900562d18fb61fb46cb31eef9bd8e66c146e5ef3ac2e20": 2,
    "a5762cbe2b09c01700a26ba4a6335c03088e8715d6cd354fbb933ca7f0d84698": 1,
    "a9dd3e82f2460d757058748d4b72b3229448ed57f0d6562a4a404cf05d58eb76": 1,
    "b6f2418fb5a77fc40dd6ace76e478a485eb06d7aa08b85e08455bfd9abf44913": 1,
    "cd4492a89109ee1bbee5a2b84731f4dbce1652e01f0ed4ee97aaeff23031c13a": 2,
    "cfb32738276db1501cf5877ac98f10d5b0aa9a302467bb01b1083ca05994d946": 2,
    "d002ad76a36be37aa1046576b91a66227ff2a704cd23efbb46d792cb271f0878": 2,
    "d346cf939d1a630402094f0560fb8140db98122d1604a58d2fd82614ff686fcd": 2,
    "d767a3d85f62cc96907bda418ca5bb6eeab39c98b88329c0ca0c60bf546a0d6e": 1,
    "fd4bafaa5c6f126cb4e6d060353df2c8af1e96fc99ab066fe51fc04bd5697732": 2,
}

# tokens that are punctuation-heavy normalize to short digit strings; keep the
# n-gram sizes we actually generated so the scanner knows what to look for.
SIZES = sorted(set(HASHES.values())) or [1]

WORD = re.compile(r"[a-z0-9]+")


def ngrams(text: str, sizes: list[int]) -> set[str]:
    words = WORD.findall(text.lower())
    out: set[str] = set()
    for n in sizes:
        for i in range(len(words) - n + 1):
            out.add(" ".join(words[i:i + n]))
    return out


def mask(s: str) -> str:
    """Never echo a matched token in full — the build log may be shared."""
    return " ".join((w[0] + "*" * max(0, len(w) - 1)) if w else w for w in s.split(" "))


def scan_file(path: str) -> list[tuple[str, str]]:
    text = open(path, encoding="utf-8", errors="ignore").read()
    hits: list[tuple[str, str]] = []
    for gram in ngrams(text, SIZES):
        h = hashlib.sha256(gram.encode()).hexdigest()
        if h in HASHES:
            hits.append((gram, h[:12]))
    return hits


def main(argv: list[str]) -> int:
    root = argv[1] if len(argv) > 1 else "dist"
    files = sorted(glob.glob(os.path.join(root, "*.html")))
    if not files:
        print(f"gate: no HTML found under {root!r}", file=sys.stderr)
        return 2
    failed = False
    for f in files:
        hits = scan_file(f)
        if hits:
            failed = True
            for gram, digest in hits:
                print(f"PII GATE FAILED: {os.path.basename(f)} matched {mask(gram)} (sha {digest})",
                      file=sys.stderr)
    if failed:
        print("PII gate FAILED — nothing should be deployed.", file=sys.stderr)
        return 1
    print(f"PII gate clean over {len(files)} page(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
