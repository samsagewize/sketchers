// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {MyMilio} from "./MyMilio.sol";

contract EthereumBridgeMinter is AccessControl, Pausable, ReentrancyGuard {
    bytes32 public constant RELAYER_ROLE = keccak256("RELAYER_ROLE");
    uint256 public constant MAX_BATCH_SIZE = 50;

    MyMilio public immutable myMilio;
    mapping(bytes32 abstractDepositId => bool processed) public processedAbstractDeposits;

    event BridgeFinalized(
        bytes32 indexed abstractDepositId,
        address indexed recipient,
        uint256[] tokenIds
    );

    constructor(address admin, address myMilioContract) {
        require(admin != address(0), "admin required");
        require(myMilioContract != address(0), "collection required");
        myMilio = MyMilio(myMilioContract);
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(RELAYER_ROLE, admin);
    }

    function finalizeBridge(
        bytes32 abstractDepositId,
        address recipient,
        uint256[] calldata tokenIds
    ) external onlyRole(RELAYER_ROLE) nonReentrant whenNotPaused {
        require(abstractDepositId != bytes32(0), "deposit id required");
        require(!processedAbstractDeposits[abstractDepositId], "deposit processed");
        require(recipient != address(0), "recipient required");
        require(tokenIds.length > 0, "token ids required");
        require(tokenIds.length <= MAX_BATCH_SIZE, "too many tokens");

        processedAbstractDeposits[abstractDepositId] = true;
        myMilio.batchMintFromBridge(recipient, tokenIds, abstractDepositId);

        emit BridgeFinalized(abstractDepositId, recipient, tokenIds);
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }
}
