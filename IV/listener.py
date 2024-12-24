from web3 import Web3
from web3.contract import Contract
from web3.providers.rpc import HTTPProvider
from web3.middleware import geth_poa_middleware
import json
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

source_chain = 'avax'
destination_chain = 'bsc'
contract_info = "contract_info.json"

def connectTo(chain):
    if chain == 'avax':
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc" #AVAX C-chain testnet

    if chain == 'bsc':
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/" #BSC testnet

    if chain in ['avax','bsc']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        # inject the poa compatibility middleware to the innermost layer
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3

def getContractInfo(chain):
    """
        Load the contract_info file into a dictinary
        This function is used by the autograder and will likely be useful to you
    """
    p = Path(__file__).with_name(contract_info)
    try:
        with p.open('r')  as f:
            contracts = json.load(f)
    except Exception as e:
        print( "Failed to read contract info" )
        print( "Please contact your instructor" )
        print( e )
        sys.exit(1)

    return contracts[chain]


eventfile = 'deposit_logs.csv'


def scanBlocks(chain):
    """
        chain - (string) should be either "source" or "destination"
        Scan the last 5 blocks of the source and destination chains
        Look for 'Deposit' events on the source chain and 'Unwrap' events on the destination chain
        When Deposit events are found on the source chain, call the 'wrap' function the destination chain
        When Unwrap events are found on the destination chain, call the 'withdraw' function on the source chain
    """

    if chain not in ['source', 'destination']:
        print(f"Invalid chain: {chain}")
        return

    w3 = connectTo(chain)
    contract_info = getContractInfo(chain)
    contract = w3.eth.contract(address=contract_info["address"], abi=contract_info["abi"])
    current_block = w3.eth.block_number

    if chain == 'source':
        other_chain = 'destination'
        event_name = 'Deposit'
        action_name = 'wrap'
    elif chain == 'destination':
        other_chain = 'source'
        event_name = 'Unwrap'
        action_name = 'withdraw'

    events = contract.events[event_name].create_filter(fromBlock=current_block - 5, toBlock=current_block).get_all_entries()

    for event in events:
        args = event["args"]
        if chain == 'source':  
            token = args["token"]
            recipient = args["recipient"]
            amount = args["amount"]

            other_w3 = connectTo(other_chain)
            other_contract_info = getContractInfo(other_chain)
            other_contract = other_w3.eth.contract(address=other_contract_info["address"], abi=other_contract_info["abi"])

            tx = other_contract.functions.wrap(token, recipient, amount).build_transaction({
                'from': other_w3.eth.default_account,
                'nonce': other_w3.eth.get_transaction_count(other_w3.eth.default_account),
            })
            signed_tx = other_w3.eth.account.sign_transaction(tx, "[PRIVATE_KEY]")  
            other_w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            print(f"Processed Deposit: {token} -> wrap() called on destination")

        elif chain == 'destination':  
            wrapped_token = args["wrapped_token"]
            recipient = args["to"]
            amount = args["amount"]

            other_w3 = connectTo(other_chain)
            other_contract_info = getContractInfo(other_chain)
            other_contract = other_w3.eth.contract(address=other_contract_info["address"], abi=other_contract_info["abi"])

            tx = other_contract.functions.withdraw(wrapped_token, recipient, amount).build_transaction({
                'from': other_w3.eth.default_account,
                'nonce': other_w3.eth.get_transaction_count(other_w3.eth.default_account),
            })
            signed_tx = other_w3.eth.account.sign_transaction(tx, "[PRIVATE_KEY]") 
            other_w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            print(f"Processed Unwrap: {wrapped_token} -> withdraw() called on source")
