from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
from pathlib import Path

source_chain = 'avax'
destination_chain = 'bsc'
contract_info = "contract_info.json"
PRIVATE_KEY = ""
WALLET_ADDRESS = "0xC941c92DE59F566086A8524E1CD5657feEc81Ef0"

def connectTo(chain):
    if chain == 'avax':
        api_url = "https://api.avax-test.network/ext/bc/C/rpc"
    elif chain == 'bsc':
        api_url = "https://data-seed-prebsc-1-s1.binance.org:8545/"
    else:
        raise ValueError(f"Unsupported chain: {chain}")

    w3 = Web3(Web3.HTTPProvider(api_url))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3

def getContractInfo(chain):
    p = Path(__file__).with_name(contract_info)
    try:
        with p.open('r') as f:
            contracts = json.load(f)
    except Exception as e:
        print("Failed to read contract info")
        raise e
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

def scanBlocks(chain):
    print(f"Received chain: {chain}")

    if chain == 'source':
        blockchain = source_chain
        event_name = "Deposit"
        other_chain = destination_chain
        other_contract_type = 'destination'
    elif chain == 'destination':
        blockchain = destination_chain
        event_name = "Unwrap"
        other_chain = source_chain
        other_contract_type = 'source'
    else:
        print(f"Invalid chain: {chain}")
        return

    try:
        w3 = connectTo(blockchain)
    except ValueError as e:
        print(f"Error connecting to chain {blockchain}: {e}")
        return

    try:
        contract_details = getContractInfo(chain)
        contract = w3.eth.contract(address=contract_details["address"], abi=contract_details["abi"])
        current_block = w3.eth.block_number
        start_block = current_block - 5
        end_block = current_block

        print(f"Scanning blocks {start_block} to {end_block} for events: {event_name}")
        events = contract.events[event_name].create_filter(
            fromBlock=start_block,
            toBlock=end_block
        ).get_all_entries()

        if not events:
            print(f"No {event_name} events found in blocks {start_block} to {end_block}.")
        else:
            print(f"Found {len(events)} {event_name} events.")
    except Exception as e:
        print(f"Error fetching events: {e}")
        return

    for event in events:
        args = event["args"]

        if chain == 'source':  
            token = args["token"]
            recipient = args["recipient"]
            amount = args["amount"]

            try:
                other_w3 = connectTo(other_chain)
                other_contract_details = getContractInfo(other_contract_type)
                other_contract = other_w3.eth.contract(
                    address=other_contract_details["address"], 
                    abi=other_contract_details["abi"]
                )

                print(f"Processing Deposit event: token={token}, recipient={recipient}, amount={amount}")
                tx = other_contract.functions.wrap(token, recipient, amount).build_transaction({
                    'from': WALLET_ADDRESS,
                    'nonce': other_w3.eth.get_transaction_count(WALLET_ADDRESS),
                    'gas': 800000,  
                    'gasPrice': other_w3.to_wei('20', 'gwei'),
                })
                receipt = sign_and_send_transaction(other_w3, tx)
                print(f"Wrap transaction successful: {receipt.transactionHash.hex()}")
            except Exception as e:
                print(f"Error processing Deposit event: {e}")

        elif chain == 'destination':  
            wrapped_token = args["underlying_token"]
            recipient = args["to"]
            amount = args["amount"]

            try:
                other_w3 = connectTo(other_chain)
                other_contract_details = getContractInfo(other_contract_type)
                other_contract = other_w3.eth.contract(
                    address=other_contract_details["address"], 
                    abi=other_contract_details["abi"]
                )

                print(f"Processing Unwrap event: wrapped_token={wrapped_token}, recipient={recipient}, amount={amount}")
                tx = other_contract.functions.withdraw(wrapped_token, recipient, amount).build_transaction({
                    'from': WALLET_ADDRESS,
                    'nonce': other_w3.eth.get_transaction_count(WALLET_ADDRESS),
                    'gas': 800000,  
                    'gasPrice': other_w3.to_wei('20', 'gwei'),
                })
                receipt = sign_and_send_transaction(other_w3, tx)
                print(f"Withdraw transaction successful: {receipt.transactionHash.hex()}")
            except Exception as e:
                print(f"Error processing Unwrap event: {e}")
