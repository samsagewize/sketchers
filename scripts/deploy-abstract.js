import hre from "hardhat";

const { ethers } = hre;

async function main() {
  const [deployer] = await ethers.getSigners();
  const sketchyMilioContract = process.env.SKETCHYMILIO_CONTRACT;

  if (!ethers.isAddress(sketchyMilioContract)) {
    throw new Error("Set SKETCHYMILIO_CONTRACT in .env before deploying");
  }

  console.log(`Deploying Abstract bridge from ${deployer.address}`);

  const AbstractSketchyMilioBridge = await ethers.getContractFactory("AbstractSketchyMilioBridge");
  const bridge = await AbstractSketchyMilioBridge.deploy(deployer.address, sketchyMilioContract);
  await bridge.waitForDeployment();

  console.log(`AbstractSketchyMilioBridge deployed: ${await bridge.getAddress()}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
