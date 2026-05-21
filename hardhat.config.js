import "@nomicfoundation/hardhat-toolbox";
import dotenv from "dotenv";

dotenv.config();

const accounts = process.env.DEPLOYER_PRIVATE_KEY
  ? [process.env.DEPLOYER_PRIVATE_KEY]
  : [];

export default {
  solidity: {
    version: "0.8.25",
    settings: {
      evmVersion: "cancun",
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    ethereum: {
      url: process.env.ETHEREUM_RPC_URL || "",
      chainId: 1,
      accounts
    },
    abstract: {
      url: process.env.ABSTRACT_RPC_URL || "https://api.mainnet.abs.xyz",
      chainId: 2741,
      accounts
    }
  }
};
