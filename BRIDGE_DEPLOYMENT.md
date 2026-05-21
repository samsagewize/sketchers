# MyMilio Bridge Deployment

This repo includes a v1 lock-and-mint bridge setup:

- `AbstractSketchyMilioBridge` deploys on Abstract and locks the original SketchyMilio NFTs.
- `MyMilio` deploys on Ethereum Mainnet and creates the destination ERC-721 collection named `MyMilio`.
- `EthereumBridgeMinter` deploys on Ethereum and mints `MyMilio` NFTs after an authorized relayer verifies Abstract lock events.

This v1 uses a trusted relayer role. Before handling meaningful value, get the contracts audited or replace the relayer with a battle-tested cross-chain messaging layer such as LayerZero ONFT.

## Setup

1. Copy `.env.example` to `.env`.
2. Fill in `DEPLOYER_PRIVATE_KEY`, `ETHEREUM_RPC_URL`, and `MYMILIO_BASE_URI`.
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
3. Save the Abstract `AbstractSketchyMilioBridge` address.
4. Put the Abstract bridge address into `templates/bridge.html` as `BRIDGE_CONTRACT`.
5. If you use a separate relayer wallet, grant it `RELAYER_ROLE` on both bridge contracts.
6. Verify the contracts on Etherscan/Abscan.

## Bridge Flow

1. User approves `AbstractSketchyMilioBridge` for their SketchyMilios.
2. User calls `bridgeToEthereum(tokenIds, ethereumRecipient)` on Abstract.
3. The Abstract bridge locks the NFTs and emits `BridgeToEthereumInitiated`.
4. Relayer verifies the event and calls `finalizeBridge(depositId, recipient, tokenIds)` on Ethereum.
5. Ethereum `MyMilio` collection mints matching token IDs to the recipient.

To support returning from Ethereum to Abstract, users burn their Ethereum `MyMilio` tokens with `burnForBridge`, then the relayer calls `releaseFromEthereum` on Abstract.
