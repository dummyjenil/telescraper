"""
Regex Data Extractor.
Extracts emails, phone numbers, URLs, Telegram mentions, and crypto wallets (BTC, ETH, TON, Solana, USDT)
directly from scraped messages.
"""

import re
from typing import Dict, List

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
URL_PATTERN = re.compile(
    r"https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_+.~#?&/=]*)"
)
MENTION_PATTERN = re.compile(r"@([a-zA-Z0-9_]{4,32})")

# Crypto wallet address patterns
BTC_PATTERN = re.compile(r"\b(?:[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59})\b")
ETH_PATTERN = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
SOLANA_PATTERN = re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b")
TON_PATTERN = re.compile(r"\b(?:EQ|UQ|kQ)[a-zA-Z0-9_-]{46}\b")
TRON_PATTERN = re.compile(r"\bT[A-Za-z1-9]{33}\b")


def extract_data(text: str) -> Dict[str, List[str]]:
    """
    Extract all structured entities and crypto addresses from input text.

    :param text: Message string
    :return: Dictionary containing extracted lists of emails, phones, urls, mentions, and wallets
    """
    if not text:
        return {
            "emails": [],
            "phones": [],
            "urls": [],
            "mentions": [],
            "wallets": {"bitcoin": [], "ethereum": [], "solana": [], "ton": [], "tron": []},
        }

    emails = sorted(list(set(EMAIL_PATTERN.findall(text))))
    urls = sorted(list(set(URL_PATTERN.findall(text))))
    mentions = sorted(list(set(MENTION_PATTERN.findall(text))))

    # Phone number filtering (require at least 7 digits)
    raw_phones = PHONE_PATTERN.findall(text)
    phones = sorted(list(set([p.strip() for p in raw_phones if len(re.sub(r"\D", "", p)) >= 7])))

    # Crypto Wallets
    btc = sorted(list(set(BTC_PATTERN.findall(text))))
    eth = sorted(list(set(ETH_PATTERN.findall(text))))
    ton = sorted(list(set(TON_PATTERN.findall(text))))
    tron = sorted(list(set(TRON_PATTERN.findall(text))))
    sol = sorted(list(set(SOLANA_PATTERN.findall(text))))

    # Exclude ETH/BTC/TON false positives from Solana matches
    sol_filtered = [s for s in sol if s not in btc and s not in tron and len(s) >= 32]

    return {
        "emails": emails,
        "phones": phones,
        "urls": urls,
        "mentions": mentions,
        "wallets": {"bitcoin": btc, "ethereum": eth, "solana": sol_filtered, "ton": ton, "tron": tron},
    }
