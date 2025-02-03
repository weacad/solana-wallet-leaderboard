<<<<<<< HEAD
import requests
import pandas as pd
import json
from config import HELIUS_KEY
import time
# Helius API endpoint
BASE_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_KEY}"

def get_transactions(wallet_address, n=50):
    """
    Fetch up to n transaction signatures for the given wallet.
    Returns a list of signatures or an empty list on failure.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [wallet_address, {"limit": n}],
    }
    try:
        response = requests.post(BASE_URL, json=payload)
        if response.status_code == 429:
            time.sleep(2)
            response = requests.post(BASE_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            return data.get("result", [])
        else:
            print(f"get_transactions failed with status {response.status_code}")
    except Exception as e:
        print(f"Error fetching signatures for {wallet_address}: {e}")
    # Fall back to an empty list if anything goes wrong
    return []

def get_transaction_details(signature):
    """
    Retrieve the transaction details for a given signature from Helius.
    Returns a dictionary with transaction data or an empty dict on failure.
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
    try:
        response = requests.post(BASE_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            # Return the "result" field if present, otherwise an empty dict
            return data.get("result", {})
        else:
            print(f"Failed to fetch transaction details for {signature}, status {response.status_code}")
    except Exception as e:
        print(f"Error parsing transaction details for {signature}: {e}")
    # On error, return empty dict instead of None
    return {}

def export_trades(wallet_address, n=100):
    """
    Exports desired columns of transaction data (Time, Wallet Delta).
    Returns a dataframe with two columns:
        Time          -> blockTime (Unix epoch)
        Wallet Delta  -> change in lamports for that wallet in this transaction
    """
    times = []
    holdings_delta = []
    transactions = get_transactions(wallet_address, n)

    for tx in transactions:
        tx_details = get_transaction_details(tx["signature"])

        # Safely check for "transaction" and "meta" keys
        if "transaction" not in tx_details or "meta" not in tx_details:
            continue

        transaction_info = tx_details["transaction"]
        meta_info = tx_details["meta"]

        # Make sure we have accountKeys, preBalances, and postBalances
        if "message" not in transaction_info:
            continue
        account_keys = transaction_info["message"].get("accountKeys", [])
        if "preBalances" not in meta_info or "postBalances" not in meta_info:
            continue

        # Check if wallet_address is in accountKeys
        try:
            wallet_i = account_keys.index(wallet_address)
        except ValueError:
            # The wallet address isn't one of the account keys; skip
            continue

        # Check that we have valid balances for that index
        pre_bal = meta_info["preBalances"]
        post_bal = meta_info["postBalances"]
        if wallet_i >= len(pre_bal) or wallet_i >= len(post_bal):
            continue

        # Calculate the delta
        change = post_bal[wallet_i] - pre_bal[wallet_i]
        block_time = tx_details.get("blockTime", None)
        if block_time is None:
            # No blockTime => skip
            continue

        times.append(block_time)
        holdings_delta.append(change)

    # Build a DataFrame
    df = pd.DataFrame({
        "Time": times,
        "Wallet Delta": holdings_delta
    })

    # Convert lamports to SOL
    df["Wallet Delta"] = df["Wallet Delta"] / 1_000_000_000
    return df
=======
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
>>>>>>> 7863c98ef57d1bfb4fb912c6e8fd771fc93e6867
