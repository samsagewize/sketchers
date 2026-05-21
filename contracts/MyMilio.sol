// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";

contract MyMilio is ERC721, AccessControl {
    bytes32 public constant BRIDGE_ROLE = keccak256("BRIDGE_ROLE");
    uint256 public constant MAX_BATCH_SIZE = 50;

    string private collectionBaseURI;
    mapping(uint256 tokenId => bytes32 sourceDepositId) public bridgedFromDeposit;

    event BaseURIUpdated(string baseURI);
    event BridgeMinted(address indexed to, uint256 indexed tokenId, bytes32 indexed sourceDepositId);
    event BridgeBurned(address indexed owner, uint256 indexed tokenId, bytes32 indexed returnId);

    constructor(address admin, string memory initialBaseURI) ERC721("MyMilio", "MYMILIO") {
        require(admin != address(0), "admin required");
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(BRIDGE_ROLE, admin);
        collectionBaseURI = initialBaseURI;
    }

    function setBaseURI(string calldata newBaseURI) external onlyRole(DEFAULT_ADMIN_ROLE) {
        collectionBaseURI = newBaseURI;
        emit BaseURIUpdated(newBaseURI);
    }

    function mintFromBridge(
        address to,
        uint256 tokenId,
        bytes32 sourceDepositId
    ) external onlyRole(BRIDGE_ROLE) {
        require(to != address(0), "recipient required");
        require(sourceDepositId != bytes32(0), "deposit id required");
        bridgedFromDeposit[tokenId] = sourceDepositId;
        _safeMint(to, tokenId);
        emit BridgeMinted(to, tokenId, sourceDepositId);
    }

    function batchMintFromBridge(
        address to,
        uint256[] calldata tokenIds,
        bytes32 sourceDepositId
    ) external onlyRole(BRIDGE_ROLE) {
        require(to != address(0), "recipient required");
        require(sourceDepositId != bytes32(0), "deposit id required");
        require(tokenIds.length > 0, "token ids required");
        require(tokenIds.length <= MAX_BATCH_SIZE, "too many tokens");

        for (uint256 i = 0; i < tokenIds.length; i++) {
            uint256 tokenId = tokenIds[i];
            bridgedFromDeposit[tokenId] = sourceDepositId;
            _safeMint(to, tokenId);
            emit BridgeMinted(to, tokenId, sourceDepositId);
        }
    }

    function burnForBridge(uint256 tokenId, bytes32 returnId) external {
        address owner = ownerOf(tokenId);
        require(
            msg.sender == owner ||
                getApproved(tokenId) == msg.sender ||
                isApprovedForAll(owner, msg.sender),
            "not owner or approved"
        );
        require(returnId != bytes32(0), "return id required");

        _burn(tokenId);
        delete bridgedFromDeposit[tokenId];
        emit BridgeBurned(owner, tokenId, returnId);
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        return string.concat(collectionBaseURI, _toString(tokenId), ".json");
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }

    function _toString(uint256 value) private pure returns (string memory) {
        if (value == 0) {
            return "0";
        }

        uint256 temp = value;
        uint256 digits;
        while (temp != 0) {
            digits++;
            temp /= 10;
        }

        bytes memory buffer = new bytes(digits);
        while (value != 0) {
            digits -= 1;
            buffer[digits] = bytes1(uint8(48 + uint256(value % 10)));
            value /= 10;
        }
        return string(buffer);
    }
}
