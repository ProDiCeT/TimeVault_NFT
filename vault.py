import streamlit as st
import json
import os
import base64
import datetime
import requests
from web3 import Web3
from dotenv import load_dotenv
from PIL import Image
import hashlib
from io import BytesIO

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

load_dotenv()

RPC_URL = os.getenv("RPC_URL")
CHAIN_ID = int(os.getenv("CHAIN_ID"))
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
EXPLORER = os.getenv("EXPLORER")

# IPFS / Pinata
PINATA_API_KEY = os.getenv("PINATA_API_KEY")
PINATA_SECRET_KEY = os.getenv("PINATA_SECRET_KEY")

with open("TimeVaultNFT.json") as f:
    CONTRACT_ABI = json.load(f)

w3 = Web3(Web3.HTTPProvider(RPC_URL))

# --------------------------------------------------
# IPFS FUNCTIONS
# --------------------------------------------------

def upload_to_pinata(file_bytes, filename="image.jpg"):
    """Upload un fichier sur IPFS via Pinata"""
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    
    headers = {
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_SECRET_KEY
    }
    
    files = {
        "file": (filename, file_bytes)
    }
    
    try:
        response = requests.post(url, files=files, headers=headers)
        response.raise_for_status()
        
        ipfs_hash = response.json()["IpfsHash"]
        return ipfs_hash, None
    except Exception as e:
        return None, str(e)

def upload_metadata_to_pinata(metadata):
    """Upload les métadonnées JSON sur IPFS via Pinata"""
    url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
    
    headers = {
        "Content-Type": "application/json",
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_SECRET_KEY
    }
    
    payload = {
        "pinataContent": metadata,
        "pinataMetadata": {
            "name": "TimeVault NFT Metadata"
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        ipfs_hash = response.json()["IpfsHash"]
        return ipfs_hash, None
    except Exception as e:
        return None, str(e)

def optimize_image(image_bytes, max_size_kb=500):
    """Optimise l'image pour réduire sa taille"""
    img = Image.open(BytesIO(image_bytes))
    
    # Convertir en RGB si nécessaire
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    # Redimensionner si trop grande
    max_dimension = 1024
    if max(img.size) > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    
    # Compresser
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85, optimize=True)
    buffer.seek(0)
    
    return buffer.read()

# --------------------------------------------------
# UI
# --------------------------------------------------

st.set_page_config(page_title="🔒 TimeVault NFT", layout="wide")
st.title("🔒 TimeVault — Lock ETH & Mint On-Chain NFT")
st.caption("✨ Images stored on IPFS (decentralized)")
st.divider()

if not w3.is_connected():
    st.error("❌ RPC not reachable")
    st.stop()

if not PINATA_API_KEY or not PINATA_SECRET_KEY:
    st.error("❌ Pinata API keys not configured in .env file")
    st.stop()

# --------------------------------------------------
# WALLET CONNECTION
# --------------------------------------------------

st.header("👛 Wallet Connection")

# Initialiser session_state pour la clé privée
if 'private_key' not in st.session_state:
    st.session_state.private_key = PRIVATE_KEY if PRIVATE_KEY else None

wallet_option = st.radio(
    "Choose wallet connection method:",
    ["Use .env file", "Enter private key manually"],
    horizontal=True
)

if wallet_option == "Enter private key manually":
    private_key_input = st.text_input(
        "🔑 Private Key",
        type="password",
        placeholder="0x...",
        help="Your private key will not be stored"
    )
    
    if private_key_input:
        # Nettoyer l'input (enlever espaces, ajouter 0x si manquant)
        private_key_clean = private_key_input.strip()
        if not private_key_clean.startswith("0x"):
            private_key_clean = "0x" + private_key_clean
        
        try:
            # Valider la clé privée
            test_account = w3.eth.account.from_key(private_key_clean)
            st.session_state.private_key = private_key_clean
            st.success(f"✅ Wallet connected: `{test_account.address}`")
        except Exception as e:
            st.error(f"❌ Invalid private key: {str(e)}")
            st.session_state.private_key = None
    else:
        st.warning("⚠️ Please enter your private key")
        st.session_state.private_key = None
else:
    # Utiliser la clé du .env
    if PRIVATE_KEY:
        st.session_state.private_key = PRIVATE_KEY
        account = w3.eth.account.from_key(PRIVATE_KEY)
        st.success(f"✅ Wallet from .env: `{account.address}`")
    else:
        st.error("❌ No private key found in .env file")
        st.session_state.private_key = None

# Vérifier qu'on a une clé privée valide
if not st.session_state.private_key:
    st.error("❌ Please connect a wallet to continue")
    st.stop()

# Créer l'account et le contract
account = w3.eth.account.from_key(st.session_state.private_key)
contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=CONTRACT_ABI
)

st.divider()

# --------------------------------------------------
# NFT IMAGE UPLOAD
# --------------------------------------------------

st.header("🖼️ Vault NFT Image")

uploaded_image = st.file_uploader(
    "Upload your NFT image (PNG/JPG)",
    type=["png", "jpg", "jpeg"],
    help="Will be stored on IPFS (decentralized storage)"
)

# Initialiser session_state
if 'ipfs_image_hash' not in st.session_state:
    st.session_state.ipfs_image_hash = None

if uploaded_image:
    image_bytes = uploaded_image.read()
    
    # Afficher l'image
    st.image(image_bytes, caption="NFT preview", use_container_width=False, width=300)
    
    # Infos sur le fichier
    file_size_kb = len(image_bytes) / 1024
    st.info(f"📦 File size: {file_size_kb:.2f} KB")
    
    # Optimiser si trop grande
    if file_size_kb > 500:
        with st.spinner("Optimizing image..."):
            image_bytes = optimize_image(image_bytes)
            optimized_size_kb = len(image_bytes) / 1024
            st.success(f"✅ Image optimized: {optimized_size_kb:.2f} KB")
    
    # Hash de l'image
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    st.code(f"SHA256: {image_hash[:16]}...", language=None)
    
    # Upload vers IPFS
    if st.button("📤 Upload to IPFS", use_container_width=True):
        with st.spinner("Uploading to IPFS via Pinata..."):
            ipfs_hash, error = upload_to_pinata(image_bytes, uploaded_image.name)
            
            if error:
                st.error(f"❌ Upload failed: {error}")
            else:
                st.session_state.ipfs_image_hash = ipfs_hash
                st.success(f"✅ Uploaded to IPFS!")
                st.code(f"ipfs://{ipfs_hash}", language=None)
                st.markdown(f"[View on IPFS Gateway](https://gateway.pinata.cloud/ipfs/{ipfs_hash})")

# Afficher le statut de l'upload IPFS
if st.session_state.ipfs_image_hash:
    st.success(f"✅ Image ready: `ipfs://{st.session_state.ipfs_image_hash}`")
else:
    st.warning("⚠️ Please upload your image to IPFS before minting")

# --------------------------------------------------
# VAULT PARAMETERS
# --------------------------------------------------

st.header("🔐 Vault parameters")

col1, col2 = st.columns(2)

with col1:
    eth_amount = st.number_input(
        "ETH amount to lock",
        min_value=0.00001,
        step=0.00001,
        format="%.5f"
    )

with col2:
    unlock_date = st.date_input(
        "Unlock date",
        min_value=datetime.date.today()
    )

unlock_ts = int(
    datetime.datetime.combine(unlock_date, datetime.time.min).timestamp()
)

# --------------------------------------------------
# MINT + LOCK
# --------------------------------------------------

st.divider()
st.header("🚀 Create Vault & Mint NFT")

if st.button("🔒 Lock ETH & Mint NFT", use_container_width=True, type="primary"):

    if not st.session_state.ipfs_image_hash:
        st.error("❌ Please upload your image to IPFS first")
        st.stop()

    value = w3.to_wei(eth_amount, "ether")

    # Créer les métadonnées
    metadata = {
        "name": "TimeVault Lock NFT",
        "description": f"Proof of {eth_amount} ETH locked until {unlock_date}",
        "image": f"ipfs://{st.session_state.ipfs_image_hash}",
        "attributes": [
            {"trait_type": "Unlock Date", "value": str(unlock_date)},
            {"trait_type": "Amount", "value": f"{eth_amount} ETH"},
            {"trait_type": "Network", "value": "Base"},
            {"trait_type": "Unlock Timestamp", "value": unlock_ts}
        ]
    }

    # Upload métadonnées vers IPFS
    with st.spinner("Uploading metadata to IPFS..."):
        metadata_hash, error = upload_metadata_to_pinata(metadata)
        
        if error:
            st.error(f"❌ Metadata upload failed: {error}")
            st.stop()
        
        st.success(f"✅ Metadata uploaded: `{metadata_hash}`")

    # Construire la transaction
    token_uri = f"ipfs://{metadata_hash}"
    
    st.info(f"📝 Token URI: `{token_uri}`")

    try:
        nonce = w3.eth.get_transaction_count(account.address)

        tx = contract.functions.deposit(
            unlock_ts,
            token_uri
        ).build_transaction({
            "from": account.address,
            "value": value,
            "nonce": nonce,
            "gas": 300000,
            "maxFeePerGas": w3.eth.gas_price + w3.to_wei(0.1, "gwei"),
            "maxPriorityFeePerGas": w3.to_wei(0.1, "gwei"),
            "chainId": CHAIN_ID
        })

        with st.spinner("Signing and sending transaction..."):
            signed = w3.eth.account.sign_transaction(tx, st.session_state.private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction).hex()

        st.success("✅ Vault created & NFT minted!")
        st.balloons()
        
        st.markdown(f"**Transaction:** [{tx_hash[:16]}...]({EXPLORER}/tx/{tx_hash})")
        st.markdown(f"**Image:** [View on IPFS](https://gateway.pinata.cloud/ipfs/{st.session_state.ipfs_image_hash})")
        st.markdown(f"**Metadata:** [View on IPFS](https://gateway.pinata.cloud/ipfs/{metadata_hash})")
        
        # Réinitialiser après le mint
        st.session_state.ipfs_image_hash = None
        
    except Exception as e:
        st.error(f"❌ Transaction failed: {str(e)}")

# --------------------------------------------------
# WITHDRAW (AUTO-BURN NFT)
# --------------------------------------------------

st.divider()
st.header("🔓 Withdraw ETH")

st.warning("⚠️ **Important:** The NFT will be automatically burned (destroyed) after withdrawing your ETH. This action is irreversible!")

vault_id_input = st.number_input("Vault ID", min_value=1, step=1, key="vault_id")

if st.button("💸 Withdraw ETH & Burn NFT", use_container_width=True, type="primary"):
    try:
        # Récupérer le tokenId associé au vaultId
        token_id = contract.functions.getTokenIdByVault(vault_id_input).call()
        
        # Étape 1: Withdraw ETH
        with st.spinner("Step 1/2: Withdrawing ETH..."):
            nonce = w3.eth.get_transaction_count(account.address)

            tx = contract.functions.withdraw(vault_id_input).build_transaction({
                "from": account.address,
                "nonce": nonce,
                "gas": 200000,
                "maxFeePerGas": w3.eth.gas_price + w3.to_wei(0.1, "gwei"),
                "maxPriorityFeePerGas": w3.to_wei(0.1, "gwei"),
                "chainId": CHAIN_ID
            })

            signed = w3.eth.account.sign_transaction(tx, st.session_state.private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction).hex()

        st.success("✅ ETH withdrawn successfully!")
        st.markdown(f"**Withdrawal transaction:** [{tx_hash[:16]}...]({EXPLORER}/tx/{tx_hash})")
        
        # Étape 2: Burn automatique du NFT
        with st.spinner("Step 2/2: Burning NFT..."):
            import time
            time.sleep(3)  # Attendre confirmation de la transaction précédente
            
            nonce = w3.eth.get_transaction_count(account.address)
            
            # Utiliser le tokenId, pas le vaultId
            burn_tx = contract.functions.burn(token_id).build_transaction({
                "from": account.address,
                "nonce": nonce,
                "gas": 150000,
                "maxFeePerGas": w3.eth.gas_price + w3.to_wei(0.1, "gwei"),
                "maxPriorityFeePerGas": w3.to_wei(0.1, "gwei"),
                "chainId": CHAIN_ID
            })
            
            signed_burn = w3.eth.account.sign_transaction(burn_tx, st.session_state.private_key)
            burn_tx_hash = w3.eth.send_raw_transaction(signed_burn.raw_transaction).hex()
        
        st.success("🔥 NFT burned successfully!")
        st.markdown(f"**Burn transaction:** [{burn_tx_hash[:16]}...]({EXPLORER}/tx/{burn_tx_hash})")
        st.info(f"🎫 Token ID {token_id} has been permanently destroyed")
        st.balloons()
        
    except Exception as e:
        st.error(f"❌ Operation failed: {str(e)}")
        st.info("💡 Make sure the vault is unlocked and you own the NFT")

# --------------------------------------------------
# INFO SECTION
# --------------------------------------------------

st.divider()

with st.expander("ℹ️ How Withdrawal Works"):
    st.markdown("""
    ### Withdrawal Process
    
    When you withdraw your locked ETH, **the NFT is automatically burned** in a 2-step process:
    
    1. **Step 1:** Withdraw your ETH from the vault
    2. **Step 2:** The NFT is immediately burned (destroyed)
    
    ### Why Burn the NFT?
    
    - ✅ **Clean**: Your wallet stays organized
    - ✅ **Privacy**: No trace of the lock after withdrawal
    - ✅ **Security**: The NFT proof disappears with the lock
    - ✅ **Deflationary**: Reduces total NFT supply
    
    ### Important Notes:
    
    ⚠️ **This is automatic and irreversible**  
    ⚠️ **The vault must be unlocked** (past the unlock date)  
    ⚠️ **You must own the NFT** to withdraw  
    ⚠️ **Gas fees apply** for both transactions (withdraw + burn)  
    """)

# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()
st.caption("🌐 Images & metadata stored on IPFS | 🔥 NFTs automatically burned on withdrawal")