import hre from "hardhat";

const { ethers } = hre;

async function main() {
  const [deployer] = await ethers.getSigners();
  const baseURI = process.env.MYMILIO_BASE_URI || "";

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
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
