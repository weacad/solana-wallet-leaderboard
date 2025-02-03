import requests
import pandas as pd
import json
from config import HELIUS_KEY


# Helius API endpoint
BASE_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_KEY}"


def get_transactions(wallet_address, n=50):
    """
    Args:
        wallet_address (str): desired solana wallet address
        n (int): number of return signatures desired
    Returns:
        List of n transactions made by wallet
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [wallet_address, {"limit": n}],
    }
    response = requests.post(BASE_URL, json=payload)
    if response.status_code == 200:
        return response.json().get("result", [])
    return []


def is_radium_swap(transaction):
    """
    Checks if transaction was a radium swap (filters out bot trades pretty sure)
    Args:
        transaction (str)
    Returns:
        is_swap (bool): if transaction has radium_swap instruction
    """


def get_transaction_details(signature):
    """
    Args:
        signature (str): Unique string representing unique transaction hash

    Returns:
        dictionary: json of transaction details
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {
                "encoding": "json",
                "commitment": "confirmed",
                "maxSupportedTransactionVersion": 0,
            },
        ],
    }
    response = requests.post(BASE_URL, json=payload)
    if response.status_code == 200:
        return response.json().get("result", {})
    else:
        print("failed")
    return {}


def export_trades(wallet_address, n=100):
    """
    Exports desired columns of transaction data

    Args:
        wallet_address (str): Desired wallet address data comes from

    Returns:
        df (dataframe): blocktime, holdings_delta
    """

    times = []
    holdings_delta = []
    transactions = get_transactions(wallet_address, n)

    for tx in transactions:
        # first get the information on the trade
        tx_details = get_transaction_details(tx["signature"])
        if "transaction" in tx_details:
            # next find the wallet_index (this is consistent across keys)
            wallet_i = int(tx_details["transaction"]["message"]["accountKeys"].index(wallet_address))

            # use the wallet address to get the pre and post balance of the trade
            change = tx_details["meta"]["postBalances"][wallet_i] - tx_details["meta"]["preBalances"][wallet_i]
            holdings_delta.append(change)

            times.append(tx_details["blockTime"])

    # concat to single df
    df = pd.DataFrame({"Time": times, "Wallet Delta": holdings_delta})

    # convert from lamports to SOL
    df["Wallet Delta"] = df["Wallet Delta"] / 1_000_000_000
    return df
