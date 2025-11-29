// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract TimeVaultNFT is ERC721URIStorage, ReentrancyGuard {
    struct Vault {
        address owner;
        uint256 amount;
        uint256 unlockTime;
        bool withdrawn;
    }

    uint256 public vaultCount;
    uint256 public tokenCount;
    
    // Maximum lock duration to prevent indefinite locking (10 years)
    uint256 public constant MAX_LOCK_DURATION = 365 days * 10;
    
    mapping(uint256 => Vault) public vaults;
    mapping(uint256 => uint256) public tokenToVault; // Maps tokenId to vaultId
    mapping(uint256 => uint256) public vaultToToken; // Maps vaultId to tokenId (optimization)

    event VaultCreated(
        uint256 indexed vaultId,
        address indexed owner,
        uint256 amount,
        uint256 unlockTime,
        uint256 tokenId
    );
    
    event VaultWithdrawn(
        uint256 indexed vaultId,
        address indexed owner,
        uint256 amount
    );

    event NFTBurned(
        uint256 indexed tokenId,
        uint256 indexed vaultId,
        address indexed owner
    );

    constructor() ERC721("TimeVault Proof", "TVLT") {}

    /**
     * @notice Deposits ETH into a time-locked vault and mints an NFT as proof
     * @param unlockTime Unlock timestamp
     * @param tokenURI Metadata URI of the NFT
     */
    function deposit(
        uint256 unlockTime,
        string calldata tokenURI
    ) external payable nonReentrant {
        require(msg.value > 0, "Amount must be greater than 0");
        require(unlockTime > block.timestamp, "Invalid unlock time");
        require(
            unlockTime <= block.timestamp + MAX_LOCK_DURATION,
            "Lock duration too long"
        );

        vaultCount++;
        tokenCount++;

        vaults[vaultCount] = Vault({
            owner: msg.sender,
            amount: msg.value,
            unlockTime: unlockTime,
            withdrawn: false
        });

        tokenToVault[tokenCount] = vaultCount;
        vaultToToken[vaultCount] = tokenCount; // Reverse mapping for optimization

        _safeMint(msg.sender, tokenCount);
        _setTokenURI(tokenCount, tokenURI);

        emit VaultCreated(
            vaultCount,
            msg.sender,
            msg.value,
            unlockTime,
            tokenCount
        );
    }

    /**
     * @notice Withdraws funds from an unlocked vault
     * @param vaultId Vault ID
     */
    function withdraw(uint256 vaultId) external nonReentrant {
        // Explicit check for vault existence
        require(vaultId > 0 && vaultId <= vaultCount, "Vault does not exist");
        
        Vault storage v = vaults[vaultId];
        
        require(v.owner != address(0), "Invalid vault");
        require(msg.sender == v.owner, "Not the owner");
        require(!v.withdrawn, "Already withdrawn");
        require(block.timestamp >= v.unlockTime, "Vault still locked");
        require(v.amount > 0, "No funds to withdraw");

        uint256 amount = v.amount;
        v.withdrawn = true;
        v.amount = 0;

        (bool success, ) = payable(msg.sender).call{value: amount}("");
        require(success, "Transfer failed");

        emit VaultWithdrawn(vaultId, msg.sender, amount);
    }

    /**
     * @notice Burns (destroys) an NFT associated with a vault
     * @param tokenId NFT token ID to burn
     * @dev Only the NFT owner can burn it
     * @dev The vault must have been withdrawn (withdrawn = true)
     */
    function burn(uint256 tokenId) external {
        // Verify caller is the NFT owner
        require(ownerOf(tokenId) == msg.sender, "Not the NFT owner");
        
        // Get associated vaultId
        uint256 vaultId = tokenToVault[tokenId];
        require(vaultId > 0, "Token not associated with a vault");
        
        // Verify funds have been withdrawn
        Vault storage v = vaults[vaultId];
        require(v.withdrawn, "Funds must be withdrawn before burning NFT");
        
        // Delete reverse mapping
        delete vaultToToken[vaultId];
        
        // Burn the NFT
        _burn(tokenId);
        
        // Emit event
        emit NFTBurned(tokenId, vaultId, msg.sender);
    }

    /**
     * @notice Finds the tokenId associated with a vaultId (optimized with reverse mapping)
     * @param vaultId Vault ID
     * @return tokenId Associated NFT token ID
     */
    function getTokenIdByVault(uint256 vaultId) public view returns (uint256) {
        require(vaultId > 0 && vaultId <= vaultCount, "Vault does not exist");
        
        uint256 tokenId = vaultToToken[vaultId];
        
        // Verify token exists and has not been burned
        if (tokenId > 0) {
            try this.ownerOf(tokenId) returns (address) {
                return tokenId;
            } catch {
                revert("Token has been burned");
            }
        }
        
        revert("No token found for this vault");
    }

    /**
     * @notice Function to receive accidental ETH (rejects)
     */
    receive() external payable {
        revert("Use deposit() function");
    }

    /**
     * @notice Fallback to reject unrecognized calls
     */
    fallback() external payable {
        revert("Function does not exist");
    }

    /**
     * @notice Retrieves vault information
     * @param vaultId Vault ID
     */
    function getVaultInfo(uint256 vaultId) external view returns (
        address owner,
        uint256 amount,
        uint256 unlockTime,
        bool withdrawn,
        bool isUnlocked
    ) {
        // Explicit check for vault existence
        require(vaultId > 0 && vaultId <= vaultCount, "Vault does not exist");
        
        Vault memory v = vaults[vaultId];
        
        // Verify vault has been initialized
        require(v.owner != address(0), "Invalid vault");
        
        return (
            v.owner,
            v.amount,
            v.unlockTime,
            v.withdrawn,
            block.timestamp >= v.unlockTime
        );
    }

    /**
     * @notice Retrieves the vaultId associated with a token
     * @param tokenId NFT token ID
     */
    function getVaultIdByToken(uint256 tokenId) external view returns (uint256) {
        require(tokenId > 0 && tokenId <= tokenCount, "Token does not exist");
        uint256 vaultId = tokenToVault[tokenId];
        require(vaultId > 0, "Token not associated with a vault");
        return vaultId;
    }

    /**
     * @notice Checks if a vault exists and is valid
     * @param vaultId Vault ID
     */
    function vaultExists(uint256 vaultId) public view returns (bool) {
        return vaultId > 0 && vaultId <= vaultCount && vaults[vaultId].owner != address(0);
    }

    /**
     * @notice Checks if a token exists and has not been burned
     * @param tokenId Token ID
     */
    function tokenExists(uint256 tokenId) public view returns (bool) {
        if (tokenId == 0 || tokenId > tokenCount) {
            return false;
        }
        
        try this.ownerOf(tokenId) returns (address) {
            return true;
        } catch {
            return false;
        }
    }
}