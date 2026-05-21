import hre from "hardhat";

const { ethers } = hre;

async function main() {
  const [deployer] = await ethers.getSigners();
  const baseURI = process.env.MYMILIO_BASE_URI || "";
  const rewardRate = process.env.MILIO_REWARD_RATE_PER_SECOND || "0";

  console.log(`Deploying Ethereum contracts from ${deployer.address}`);

  const MyMilio = await ethers.getContractFactory("MyMilio");
  const myMilio = await MyMilio.deploy(deployer.address, baseURI);
  await myMilio.waitForDeployment();

  const myMilioAddress = await myMilio.getAddress();
  console.log(`MyMilio deployed: ${myMilioAddress}`);

  const EthereumBridgeMinter = await ethers.getContractFactory("EthereumBridgeMinter");
  const bridgeMinter = await EthereumBridgeMinter.deploy(deployer.address, myMilioAddress);
  await bridgeMinter.waitForDeployment();

  const bridgeMinterAddress = await bridgeMinter.getAddress();
  console.log(`EthereumBridgeMinter deployed: ${bridgeMinterAddress}`);

  const bridgeRole = await myMilio.BRIDGE_ROLE();
  const grantTx = await myMilio.grantRole(bridgeRole, bridgeMinterAddress);
  await grantTx.wait();
  console.log(`Granted MyMilio BRIDGE_ROLE to ${bridgeMinterAddress}`);

  const MilioToken = await ethers.getContractFactory("MilioToken");
  const milioToken = await MilioToken.deploy(deployer.address);
  await milioToken.waitForDeployment();

  const milioTokenAddress = await milioToken.getAddress();
  console.log(`MilioToken deployed: ${milioTokenAddress}`);

  const MyMilioStaking = await ethers.getContractFactory("MyMilioStaking");
  const staking = await MyMilioStaking.deploy(
    deployer.address,
    myMilioAddress,
    milioTokenAddress,
    rewardRate
  );
  await staking.waitForDeployment();

  const stakingAddress = await staking.getAddress();
  console.log(`MyMilioStaking deployed: ${stakingAddress}`);

  const minterRole = await milioToken.MINTER_ROLE();
  const stakingGrantTx = await milioToken.grantRole(minterRole, stakingAddress);
  await stakingGrantTx.wait();
  console.log(`Granted MilioToken MINTER_ROLE to ${stakingAddress}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
