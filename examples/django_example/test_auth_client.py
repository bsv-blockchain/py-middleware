# Minimal Auth test client using py-sdk AuthFetch

import json
from pathlib import Path

from bsv.keys import PrivateKey
from bsv.wallet.wallet_impl import WalletImpl
from bsv.constants import Network
from bsv.auth.clients.auth_fetch import AuthFetch, SimplifiedFetchRequestOptions
from bsv.auth.requested_certificate_set import RequestedCertificateSet, RequestedCertificateTypeIDAndFieldList


def load_mainnet_wallet(config_path: Path) -> WalletImpl:
    with open(config_path, 'r') as f:
        cfg = json.load(f)
    if cfg.get('network') != 'mainnet':
        raise ValueError(f"wallet network is {cfg.get('network')}, expected mainnet")
    priv = PrivateKey(cfg['private_key'], network=Network.MAINNET)
    return WalletImpl(private_key=priv, permission_callback=lambda action: True, load_env=False)


def main():
    base_dir = Path(__file__).resolve().parent
    wallet_cfg = base_dir.parent / 'testnet_setup' / 'mainnet_wallet_config.json'
    wallet = load_mainnet_wallet(wallet_cfg)

    requested = RequestedCertificateSet(
        certifiers=[],
        certificate_types=RequestedCertificateTypeIDAndFieldList(),
    )

    client = AuthFetch(wallet, requested)

    url = 'http://localhost:8000/protected/'
    opts = SimplifiedFetchRequestOptions(method='GET', headers={})
    resp = client.fetch(None, url, opts)

    print('status:', getattr(resp, 'status_code', None))
    try:
        print('body:', resp.text)
    except Exception:
        pass
    print('headers:', dict(getattr(resp, 'headers', {})))


if __name__ == '__main__':
    main()
