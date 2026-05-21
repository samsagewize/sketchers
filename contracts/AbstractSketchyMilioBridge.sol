// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {IERC721} from "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import {IERC721Receiver} from "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract AbstractSketchyMilioBridge is AccessControl, IERC721Receiver, Pausable, ReentrancyGuard {
    bytes32 public constant RELAYER_ROLE = keccak256("RELAYER_ROLE");
    uint256 public constant MAX_BATCH_SIZE = 50;

    IERC721 public immutable sketchyMilio;
    uint256 public depositNonce;

    struct Deposit {
        address owner;
        address ethereumRecipient;
        uint256[] tokenIds;
        bool released;
    }

    mapping(bytes32 depositId => Deposit) private deposits;
    mapping(uint256 tokenId => bytes32 depositId) public lockedByDeposit;
    mapping(bytes32 ethereumBurnId => bool processed) public processedEthereumBurns;

    event BridgeToEthereumInitiated(
        bytes32 indexed depositId,
        address indexed owner,
        address indexed ethereumRecipient,
        uint256[] tokenIds
    );
    event LockedTokensReleased(
        bytes32 indexed ethereumBurnId,
        bytes32 indexed depositId,
        address indexed recipient,
        uint256[] tokenIds
    );

    constructor(address admin, address sketchyMilioContract) {
        require(admin != address(0), "admin required");
        require(sketchyMilioContract != address(0), "collection required");
        sketchyMilio = IERC721(sketchyMilioContract);
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(RELAYER_ROLE, admin);
    }

    function bridgeToEthereum(
        uint256[] calldata tokenIds,
        address ethereumRecipient
    ) external nonReentrant whenNotPaused returns (bytes32 depositId) {
        require(tokenIds.length > 0, "token ids required");
        require(tokenIds.length <= MAX_BATCH_SIZE, "too many tokens");
        require(ethereumRecipient != address(0), "recipient required");

        depositNonce++;
        depositId = keccak256(
            abi.encode(
                block.chainid,
                address(this),
                msg.sender,
                ethereumRecipient,
                tokenIds,
                depositNonce
            )
        );

        Deposit storage deposit = deposits[depositId];
        deposit.owner = msg.sender;
        deposit.ethereumRecipient = ethereumRecipient;

        for (uint256 i = 0; i < tokenIds.length; i++) {
            uint256 tokenId = tokenIds[i];
            require(lockedByDeposit[tokenId] == bytes32(0), "token locked");

            deposit.tokenIds.push(tokenId);
            lockedByDeposit[tokenId] = depositId;
            sketchyMilio.safeTransferFrom(msg.sender, address(this), tokenId);
        }

        emit BridgeToEthereumInitiated(depositId, msg.sender, ethereumRecipient, tokenIds);
    }

    function releaseFromEthereum(
        bytes32 ethereumBurnId,
        bytes32 depositId,
        address recipient
    ) external onlyRole(RELAYER_ROLE) nonReentrant {
        require(ethereumBurnId != bytes32(0), "burn id required");
        require(!processedEthereumBurns[ethereumBurnId], "burn processed");
        require(recipient != address(0), "recipient required");

        Deposit storage deposit = deposits[depositId];
        require(deposit.owner != address(0), "deposit missing");
        require(!deposit.released, "deposit released");

        processedEthereumBurns[ethereumBurnId] = true;
        deposit.released = true;

        uint256[] memory tokenIds = deposit.tokenIds;
        for (uint256 i = 0; i < tokenIds.length; i++) {
            uint256 tokenId = tokenIds[i];
            delete lockedByDeposit[tokenId];
            sketchyMilio.safeTransferFrom(address(this), recipient, tokenId);
        }

        emit LockedTokensReleased(ethereumBurnId, depositId, recipient, tokenIds);
    }

    function getDeposit(bytes32 depositId)
        external
        view
        returns (
            address owner,
            address ethereumRecipient,
            uint256[] memory tokenIds,
            bool released
        )
    {
        Deposit storage deposit = deposits[depositId];
        return (deposit.owner, deposit.ethereumRecipient, deposit.tokenIds, deposit.released);
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    function onERC721Received(
        address,
        address,
        uint256,
        bytes calldata
    ) external view returns (bytes4) {
        require(msg.sender == address(sketchyMilio), "unsupported nft");
        return IERC721Receiver.onERC721Received.selector;
    }
}
