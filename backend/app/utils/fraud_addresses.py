"""
Canonical registry of known fraud / sanctioned Ethereum addresses.

This is the single source of truth used by:
  - enrichment.py  (screening before ML inference)
  - graph_features.py  (computing sender_fraud_neighbor_ratio)
  - collect_transaction_data.py  (labeling training data)
  - backtest_model.py  (backtesting targets)

Sources
───────
  OFAC SDN list      — US Treasury (public domain, no API key needed)
  Known exploit addresses — publicly documented post-mortem reports
  Tornado Cash contracts — OFAC Aug 2022

To add new addresses: add them to the relevant section below.
All addresses are stored lowercase.
"""

# ── OFAC sanctioned addresses ─────────────────────────────────────────────────
# Source: https://home.treasury.gov/policy-issues/financial-sanctions
OFAC_ADDRESSES: frozenset = frozenset({
    # Tornado Cash mixers (OFAC Aug 2022)
    "0x722122df12d4e14e13ac3b6895a86e84145b6967",
    "0xdd4c48c0b24039969fc16d1cdf626eab821d3384",
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b",
    "0xd96f2b1c14db8458374d9aca76e26c3950671e4c",
    "0x4736dcf1b7a3d580672cce6e7c65cd5cc9cfba9d",
    "0xd4b88df4d29f5cedd6857912842cff3b20c8cfa3",
    "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf",
    "0xa160cdab225685da1d56aa342ad8841c3b53f291",
    "0xfd8610d20aa15b7b2e3be39b396a1bc3516c7144",
    "0xf60dd140cff0706bae9cd734ac3ae76ad9ebc32a",
    "0x22aaa7720ddd5388a3c0a3333430953c68f1849b",
    "0xba214c1c1928a32bffe790263e38b4af9bfcd659",
    "0xb1c29e6ab19a30058e97c7efe2d2d2514e522c68",
    "0x527653ea119f3e6a1f5bd18fbf9070a1a13b5d4f",
    "0x58e8dcc13be9780fc42e8723d8ead4cf46943df2",
    "0xd691f27f38b395b8edc35a13516fd3a1329fe29c",
    "0x1356c899d8c9467c7f71c195612f8a395abf2f0a",
    "0xa60c772958a3ed426c63ad5d83f18e7e7e1a4e5a",
    "0x169ad27a470d064dede56a2d3ff727986b15d52b",
    "0x0836222f2b2b5a6700c204a5e7b9bcf63d0a2ea6",
    "0xf67721a2d8f736e75a49fdd7fad2e31d8676542a",
    "0x9ad122c22b14202b4490edaf288fdb3c7cb3ff5e",
    "0x905b63fff465b9ffbf41dea908ceb12478ec7601",
    "0x07687e702b410fa43f4cb4af7fa097918ffd2730",
    "0x94a1b5cdb22c43faab4abeb5c74999895464ddaf",
    "0xb541fc07bc7619fd4062a54d96268525cbc6ffef",
    "0xce0042b868300000d44a59004da54a005ffdcf9f",
    "0x76d85b4c0fc497eecc38902397ac608000291ce1",
    # Blender.io (OFAC May 2022)
    "0x8576acc5c05d6ce88f4e49bf65bdf0c62f91353c",
    "0x1da5821544e25c636c1417ba96ade4cf6d2f9b5a",
    "0x7f367cc41522ce07553e823bf3be79a889debe1b",
    "0xd882cfc20f52f2599d84b8e8d58c7fb62cfe344b",
    "0x901bb9583b24d97e995513c6778dc6888ab6870e",
    "0xa7e5d5a720f06526557c513402f2e6b5fa20b008",
    # Hydra marketplace
    "0xcbc1ea13e80e12e5a35e79c05ce77a9d6a59e8e8",
})

# ── Known exploit / hack addresses ───────────────────────────────────────────
# Source: publicly documented post-mortems and on-chain attribution
KNOWN_HACK_ADDRESSES: frozenset = frozenset({
    # Ronin Bridge hack (Mar 2022, ~$625M)
    "0x098b716b8aaf21512996dc57eb0615e2383e2f96",
    # PolyNetwork exploit (Aug 2021, ~$611M)
    "0x0d6e286a7cfd25e0f01673702071e46191d7ed0e",
    "0xc8a65fadf0e0ddaf421f28feab69bf6e2e589963",
    # Bitfinex hackers (2016, DOJ-linked)
    "0x3696d870e8e62c84a0db8d50a4f06498cf0cd59e",
    # FTX collapse (2022, stolen funds movement)
    "0x59abf3837fa962d6853b4cc0a19513aa031fd32b",
    # Harmony Horizon Bridge hack (Jun 2022, ~$100M)
    "0x0d043128146654c7683fbf30ac98d7b2285ded00",
    # Euler Finance hack (Mar 2023, ~$197M)
    "0xb66cd966670d962c227b3eaba30a872dbfb995db",
    # BNB Bridge exploit (Oct 2022, ~$570M)
    "0x489a8756c18c0b8b24ec2a2b9ff3d4d447f79bec",
    # Wintermute hack (Sep 2022, ~$160M)
    "0xe74b28c2eae8679e3ccc3a94d5d0de83ccb84705",
    # Nomad Bridge hack (Aug 2022, ~$190M)
    "0x56d8b635a7c88fd1104d23d632af40c1e3a550a1",
})

# ── Combined set used for graph feature computation ────────────────────────────
ALL_FRAUD_ADDRESSES: frozenset = OFAC_ADDRESSES | KNOWN_HACK_ADDRESSES


def is_fraud_address(address: str) -> bool:
    """Return True if the address is in any known fraud set."""
    return address.lower() in ALL_FRAUD_ADDRESSES


def get_fraud_category(address: str) -> str:
    """Return the category of fraud for a known bad address, or empty string."""
    addr = address.lower()
    if addr in OFAC_ADDRESSES:
        return "ofac"
    if addr in KNOWN_HACK_ADDRESSES:
        return "known_exploit"
    return ""
