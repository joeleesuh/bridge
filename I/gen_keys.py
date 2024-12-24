from web3 import Web3
import eth_account
from eth_account.messages import encode_defunct
import os

def get_keys(challenge, keyId=0, filename="eth_mnemonic.txt"):
    """
    Generate a stable private key
    challenge - byte string
    keyId (integer) - which key to use
    filename - filename to read and store mnemonics

    Each mnemonic is stored on a separate line
    If fewer than (keyId+1) mnemonics have been generated, generate a new one and return that
    """

    w3 = Web3()
    
    private_key = "..."
    acct = w3.eth.account.from_key(private_key)
    eth_addr = acct.address

    msg = encode_defunct(challenge)
    signed_message = acct.sign_message(msg)

    assert eth_account.Account.recover_message(msg, signature=signed_message.signature) == eth_addr, f"Failed to sign message properly"

    return signed_message, eth_addr

if __name__ == "__main__":
    for i in range(4):
        challenge = os.urandom(64)
        sig, addr = get_keys(challenge=challenge, keyId=i)
        print(f"Address: {addr}")
        print(f"Signature: {sig.signature.hex()}")
