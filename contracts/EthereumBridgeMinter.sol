// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {MyMilio} from "./MyMilio.sol";

contract EthereumBridgeMinter is AccessControl, ReentrancyGuard {
    bytes32 public constant RELAYER_ROLE = keccak256("RELAYER_ROLE");

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
    ) external onlyRole(RELAYER_ROLE) nonReentrant {
        require(abstractDepositId != bytes32(0), "deposit id required");
        require(!processedAbstractDeposits[abstractDepositId], "deposit processed");
        require(recipient != address(0), "recipient required");
        require(tokenIds.length > 0, "token ids required");

        processedAbstractDeposits[abstractDepositId] = true;
        myMilio.batchMintFromBridge(recipient, tokenIds, abstractDepositId);

        emit BridgeFinalized(abstractDepositId, recipient, tokenIds);
    }
}
