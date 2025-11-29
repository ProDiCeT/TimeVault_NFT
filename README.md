# 🔒 TimeVault NFT

Lock ETH with a time-lock smart contract and get a proof-of-lock NFT. The NFT is automatically burned when you withdraw your funds.

## ✨ Features

- 🔐 **Time-locked ETH vaults** (up to 10 years)
- 🖼️ **NFT proof-of-lock** (image + metadata on IPFS)
- 🔥 **Auto-burn NFT** on withdrawal
- 💻 **Easy-to-use Streamlit interface**

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/yourusername/timevault-nft.git
cd timevault-nft
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```env
RPC_URL=https://mainnet.base.org
CHAIN_ID=8453
CONTRACT_ADDRESS=0xYourContractAddress
PRIVATE_KEY=0xYourPrivateKey
EXPLORER=https://basescan.org
PINATA_API_KEY=your_pinata_api_key
PINATA_SECRET_KEY=your_pinata_secret_key
```

Get Pinata API keys at [pinata.cloud](https://pinata.cloud)

### Run

```bash
streamlit run vault.py
```

## 📖 Usage

1. **Connect wallet** (use .env or enter manually)
2. **Upload image** → Click "Upload to IPFS"
3. **Set amount & unlock date**
4. **Lock & Mint** → Get your NFT
5. **Withdraw** (after unlock date) → NFT automatically burns

## 🏗️ Tech Stack

- **Smart Contract**: Solidity + OpenZeppelin
- **Blockchain**: Base Network
- **Frontend**: Streamlit + Web3.py
- **Storage**: IPFS (Pinata)

## 📜 Smart Contract

Deploy with remix IDE

Main functions:
- `deposit(unlockTime, tokenURI)` - Lock ETH & mint NFT
- `withdraw(vaultId)` - Withdraw ETH
- `burn(tokenId)` - Burn NFT (auto-called after withdrawal)

## 📁 Project Structure

```
timevault-nft/
├── vault.py              # Streamlit app
├── Vault.sol             # Smart contract
├── TimeVaultNFT.json     # Contract ABI
├── requirements.txt      # Dependencies
└── .env                  # Configuration
└── vault.jpg             # Picture for NFT
```

## 🔒 Security

- ✅ ReentrancyGuard on all functions
- ✅ OpenZeppelin contracts
- ✅ Owner-only withdrawals
- ⚠️ Always test on testnet first

## 📝 License

MIT License - see [LICENSE](LICENSE)

---
**Made with love by dnapog.base.eth**
