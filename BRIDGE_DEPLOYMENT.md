# MyMilio Bridge Deployment

This repo includes a v1 lock-and-mint bridge setup:

- `AbstractSketchyMilioBridge` deploys on Abstract and locks the original SketchyMilio NFTs.
- `MyMilio` deploys on Ethereum Mainnet and creates the destination ERC-721 collection named `MyMilio`.
- `EthereumBridgeMinter` deploys on Ethereum and mints `MyMilio` NFTs after an authorized relayer verifies Abstract lock events.
- `MilioToken` deploys on Ethereum with a hard cap of 21,000,000 `$MILIO`.
- `MyMilioStaking` deploys on Ethereum and is the only contract allowed to mint staking rewards.

This v1 uses a trusted relayer role. Before handling meaningful value, get the contracts audited or replace the relayer with a battle-tested cross-chain messaging layer such as LayerZero ONFT.

## Setup

1. Copy `.env.example` to `.env`.
2. Fill in `DEPLOYER_PRIVATE_KEY`, `ETHEREUM_RPC_URL`, `MYMILIO_BASE_URI`, and `MILIO_REWARD_RATE_PER_SECOND`.
3. Keep `SKETCHYMILIO_CONTRACT=0x08533a2b16e3db03eebd5b23210122f97dfcb97d` unless the Abstract collection address changes.

## Commands

```bash
pnpm --ignore-workspace install
pnpm --ignore-workspace compile
pnpm --ignore-workspace test
pnpm --ignore-workspace deploy:ethereum
pnpm --ignore-workspace deploy:abstract
```

## After Deploy

1. Save the Ethereum `MyMilio` contract address.
2. Save the Ethereum `EthereumBridgeMinter` address.
3. Save the Ethereum `MilioToken` contract address.
4. Save the Ethereum `MyMilioStaking` contract address.
5. Save the Abstract `AbstractSketchyMilioBridge` address.
6. Put the Abstract bridge address into `templates/bridge.html` as `BRIDGE_CONTRACT`.
7. If you use a separate relayer wallet, grant it `RELAYER_ROLE` on both bridge contracts.
8. Verify the contracts on Etherscan/Abscan.
9. Test with one low-value token before announcing the bridge.

## Safety Checklist

- Keep `DEFAULT_ADMIN_ROLE` and `RELAYER_ROLE` in a hardware wallet or multisig.
- Verify both bridge contracts in explorers before enabling the website bridge button.
- Confirm the website displays the exact Abstract bridge address before users approve.
- Leave the bridge paused if relayer monitoring is offline or suspicious.
- Do not grant `BRIDGE_ROLE` on `MyMilio` to any wallet except the Ethereum bridge minter.
- Do not grant `MINTER_ROLE` on `MilioToken` to any wallet. The staking contract should be the only minter.
- Start staking rewards paused or with a low reward rate until the staking UI and accounting are tested.
- Treat this trusted-relayer v1 as production-sensitive infrastructure, not as an audited trustless bridge.

## Bridge Flow

1. User approves `AbstractSketchyMilioBridge` for their SketchyMilios.
2. User calls `bridgeToEthereum(tokenIds, ethereumRecipient)` on Abstract.
3. The Abstract bridge locks the NFTs and emits `BridgeToEthereumInitiated`.
4. Relayer verifies the event and calls `finalizeBridge(depositId, recipient, tokenIds)` on Ethereum.
5. Ethereum `MyMilio` collection mints matching token IDs to the recipient.
6. User can stake Ethereum `MyMilio` NFTs in `MyMilioStaking`.
7. Staking mints `$MILIO` rewards over time, capped by the 21,000,000 max supply.

To support returning from Ethereum to Abstract, users burn their Ethereum `MyMilio` tokens with `burnForBridge`, then the relayer calls `releaseFromEthereum` on Abstract.
