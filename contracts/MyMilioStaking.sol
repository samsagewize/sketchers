// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {IERC721} from "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import {IERC721Receiver} from "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {MilioToken} from "./MilioToken.sol";

contract MyMilioStaking is AccessControl, IERC721Receiver, Pausable, ReentrancyGuard {
    uint256 public constant MAX_BATCH_SIZE = 50;

    IERC721 public immutable myMilio;
    MilioToken public immutable milioToken;
    uint256 public rewardRatePerSecond;

    struct StakeInfo {
        address owner;
        uint64 stakedAt;
        uint64 lastClaimedAt;
    }

    mapping(uint256 tokenId => StakeInfo) public stakes;
    mapping(address owner => uint256 count) public stakedBalance;

    event RewardRateUpdated(uint256 rewardRatePerSecond);
    event Staked(address indexed owner, uint256 indexed tokenId);
    event Unstaked(address indexed owner, uint256 indexed tokenId);
    event RewardsClaimed(address indexed owner, uint256 amount);

    constructor(
        address admin,
        address myMilioContract,
        address milioTokenContract,
        uint256 initialRewardRatePerSecond
    ) {
        require(admin != address(0), "admin required");
        require(myMilioContract != address(0), "collection required");
        require(milioTokenContract != address(0), "token required");

        myMilio = IERC721(myMilioContract);
        milioToken = MilioToken(milioTokenContract);
        rewardRatePerSecond = initialRewardRatePerSecond;

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    function setRewardRate(uint256 newRewardRatePerSecond) external onlyRole(DEFAULT_ADMIN_ROLE) {
        rewardRatePerSecond = newRewardRatePerSecond;
        emit RewardRateUpdated(newRewardRatePerSecond);
    }

    function stake(uint256[] calldata tokenIds) external nonReentrant whenNotPaused {
        require(tokenIds.length > 0, "token ids required");
        require(tokenIds.length <= MAX_BATCH_SIZE, "too many tokens");

        for (uint256 i = 0; i < tokenIds.length; i++) {
            uint256 tokenId = tokenIds[i];
            require(stakes[tokenId].owner == address(0), "already staked");

            myMilio.safeTransferFrom(msg.sender, address(this), tokenId);

            stakes[tokenId] = StakeInfo({
                owner: msg.sender,
                stakedAt: uint64(block.timestamp),
                lastClaimedAt: uint64(block.timestamp)
            });
            stakedBalance[msg.sender]++;

            emit Staked(msg.sender, tokenId);
        }
    }

    function unstake(uint256[] calldata tokenIds) external nonReentrant {
        require(tokenIds.length > 0, "token ids required");
        require(tokenIds.length <= MAX_BATCH_SIZE, "too many tokens");

        uint256 reward = _claimable(msg.sender, tokenIds);

        for (uint256 i = 0; i < tokenIds.length; i++) {
            uint256 tokenId = tokenIds[i];
            StakeInfo memory info = stakes[tokenId];
            require(info.owner == msg.sender, "not staker");

            delete stakes[tokenId];
            stakedBalance[msg.sender]--;
            myMilio.safeTransferFrom(address(this), msg.sender, tokenId);

            emit Unstaked(msg.sender, tokenId);
        }

        _mintReward(msg.sender, reward);
    }

    function claim(uint256[] calldata tokenIds) external nonReentrant whenNotPaused {
        require(tokenIds.length > 0, "token ids required");
        require(tokenIds.length <= MAX_BATCH_SIZE, "too many tokens");

        uint256 reward;
        for (uint256 i = 0; i < tokenIds.length; i++) {
            uint256 tokenId = tokenIds[i];
            StakeInfo storage info = stakes[tokenId];
            require(info.owner == msg.sender, "not staker");

            reward += _earnedSince(info.lastClaimedAt);
            info.lastClaimedAt = uint64(block.timestamp);
        }

        _mintReward(msg.sender, reward);
    }

    function claimable(address owner, uint256[] calldata tokenIds) external view returns (uint256) {
        return _claimable(owner, tokenIds);
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    function _claimable(address owner, uint256[] calldata tokenIds) private view returns (uint256 reward) {
        for (uint256 i = 0; i < tokenIds.length; i++) {
            StakeInfo memory info = stakes[tokenIds[i]];
            require(info.owner == owner, "not staker");
            reward += _earnedSince(info.lastClaimedAt);
        }
    }

    function _earnedSince(uint64 lastClaimedAt) private view returns (uint256) {
        return (block.timestamp - uint256(lastClaimedAt)) * rewardRatePerSecond;
    }

    function _mintReward(address to, uint256 amount) private {
        if (amount == 0) {
            return;
        }

        uint256 remaining = milioToken.cap() - milioToken.totalSupply();
        uint256 mintAmount = amount > remaining ? remaining : amount;
        if (mintAmount > 0) {
            milioToken.mint(to, mintAmount);
            emit RewardsClaimed(to, mintAmount);
        }
    }

    function onERC721Received(
        address,
        address,
        uint256,
        bytes calldata
    ) external view returns (bytes4) {
        require(msg.sender == address(myMilio), "unsupported nft");
        return IERC721Receiver.onERC721Received.selector;
    }
}
