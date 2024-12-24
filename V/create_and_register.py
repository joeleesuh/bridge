from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
from pathlib import Path

PRIVATE_KEY = "..."
WALLET_ADDRESS = "0xC941c92DE59F566086A8524E1CD5657feEc81Ef0"

def connectTo(chain):
    if chain == 'avax':
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc"
    elif chain == 'bsc':
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/"
    else:
        raise ValueError("Unsupported chain")
    
    w3 = Web3(Web3.HTTPProvider(api_url))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3

def getContractInfo(chain):
    contract_info_file = "contract_info.json"
    p = Path(__file__).with_name(contract_info_file)
    with p.open('r') as f:
        contracts = json.load(f)
    return contracts[chain]

def sign_and_send_transaction(w3, tx):
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
        print(f"Transaction successful: {tx_hash.hex()}")
    else:
        print(f"Transaction failed: {tx_hash.hex()}")
    return receipt

def register_token_on_source(token_address):
    w3 = connectTo('avax')
    contract_info = getContractInfo('source')
    contract = w3.eth.contract(address=contract_info["address"], abi=contract_info["abi"])
    
    tx = contract.functions.registerToken(token_address).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': w3.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 10**6,
        'gasPrice': w3.to_wei('20', 'gwei'),  
    })
    receipt = sign_and_send_transaction(w3, tx)
    print("registerToken receipt:", receipt)

def create_token_on_destination(token_address, name, symbol):
    w3 = connectTo('bsc')
    contract_info = getContractInfo('destination')
    contract = w3.eth.contract(address=contract_info["address"], abi=contract_info["abi"])
    
    tx = contract.functions.createToken(token_address, name, symbol).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': w3.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2 * 10**6,
        'gasPrice': w3.to_wei('20', 'gwei'),  
    })
    receipt = sign_and_send_transaction(w3, tx)
    print("createToken receipt:", receipt)

if __name__ == "__main__":
    TOKEN_ADDRESS_1 = "0xc677c31AD31F73A5290f5ef067F8CEF8d301e45c"
    TOKEN_ADDRESS_2 = "0x0773b81e0524447784CcE1F3808fed6AaA156eC8"
    print(f"Creating wrapped token on destination: {TOKEN_ADDRESS_2}")
    try:
        create_token_on_destination(TOKEN_ADDRESS_2, "TestToken2", "TT2")
    except Exception as e:
        print(f"Error creating wrapped token on destination: {TOKEN_ADDRESS_2}, Error: {e}")
