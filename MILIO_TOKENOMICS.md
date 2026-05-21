# $MILIO Tokenomics

`$MILIO` is designed as a staking rewards token for Ethereum `MyMilio` NFTs.

## Core Rules

- Token name: `Milio`
- Token symbol: `MILIO`
- Maximum supply: `21,000,000 MILIO`
- Initial supply: `0 MILIO`
- Public mint: none
- Admin premint: none
- Reward minting: only through `MyMilioStaking`

## Staking Flow

1. User bridges SketchyMilios from Abstract to Ethereum.
2. Ethereum `MyMilio` NFTs are minted to the user.
3. User approves the staking contract for their `MyMilio` NFTs.
4. User stakes/locks one or more `MyMilio` NFTs.
5. Rewards accrue over time using `rewardRatePerSecond` per staked NFT.
6. User can claim rewards while staked, or unstake and claim pending rewards.
7. Reward minting stops naturally when the 21M cap is reached.

## Admin Controls

- The admin can pause staking.
- The admin can unpause staking.
- The admin can update `rewardRatePerSecond`.
- The staking contract should be the only address with `MINTER_ROLE` on `MilioToken`.

## Launch Notes

Choose `MILIO_REWARD_RATE_PER_SECOND` carefully before launch. A simple way to reason about it:

```text
reward per NFT per day = rewardRatePerSecond * 86,400
```

Examples:

- `0.01 MILIO/day/NFT` = about `115740740740 wei` per second
- `0.10 MILIO/day/NFT` = about `1157407407407 wei` per second
- `1.00 MILIO/day/NFT` = about `11574074074074 wei` per second

Before deployment, decide how long you want the 21M cap to last and estimate how many NFTs may be staked.

## Safety Notes

This is not a promise of financial value. It is a rewards mechanism for holders who lock Ethereum `MyMilio` NFTs. Do not deploy publicly until the contracts and reward settings are reviewed, tested with a small wallet, and preferably audited.
