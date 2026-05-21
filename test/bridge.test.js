import { expect } from "chai";
import hre from "hardhat";

const { ethers } = hre;

describe("MyMilio bridge v1", function () {
  async function deployFixture() {
    const [admin, holder, relayer, recipient] = await ethers.getSigners();

    const MockSketchyMilio = await ethers.getContractFactory("MockSketchyMilio");
    const sketchy = await MockSketchyMilio.deploy();
    await sketchy.waitForDeployment();

    const MyMilio = await ethers.getContractFactory("MyMilio");
    const myMilio = await MyMilio.deploy(admin.address, "ipfs://mymilio/");
    await myMilio.waitForDeployment();

    const AbstractBridge = await ethers.getContractFactory("AbstractSketchyMilioBridge");
    const abstractBridge = await AbstractBridge.deploy(admin.address, await sketchy.getAddress());
    await abstractBridge.waitForDeployment();

    const EthereumBridgeMinter = await ethers.getContractFactory("EthereumBridgeMinter");
    const ethereumMinter = await EthereumBridgeMinter.deploy(admin.address, await myMilio.getAddress());
    await ethereumMinter.waitForDeployment();

    await myMilio.grantRole(await myMilio.BRIDGE_ROLE(), await ethereumMinter.getAddress());
    await ethereumMinter.grantRole(await ethereumMinter.RELAYER_ROLE(), relayer.address);
    await abstractBridge.grantRole(await abstractBridge.RELAYER_ROLE(), relayer.address);

    await sketchy.mint(holder.address, 7);
    await sketchy.mint(holder.address, 42);

    return { admin, holder, relayer, recipient, sketchy, myMilio, abstractBridge, ethereumMinter };
  }

  it("locks SketchyMilios on Abstract and mints MyMilio on Ethereum", async function () {
    const { holder, relayer, recipient, sketchy, myMilio, abstractBridge, ethereumMinter } =
      await deployFixture();

    const abstractBridgeAddress = await abstractBridge.getAddress();
    await sketchy.connect(holder).setApprovalForAll(abstractBridgeAddress, true);

    const tx = await abstractBridge
      .connect(holder)
      .bridgeToEthereum([7, 42], recipient.address);
    const receipt = await tx.wait();
    const event = receipt.logs
      .map((log) => {
        try {
          return abstractBridge.interface.parseLog(log);
        } catch {
          return null;
        }
      })
      .find((parsed) => parsed?.name === "BridgeToEthereumInitiated");

    const depositId = event.args.depositId;

    expect(await sketchy.ownerOf(7)).to.equal(abstractBridgeAddress);
    expect(await sketchy.ownerOf(42)).to.equal(abstractBridgeAddress);

    await ethereumMinter
      .connect(relayer)
      .finalizeBridge(depositId, recipient.address, [7, 42]);

    expect(await myMilio.name()).to.equal("MyMilio");
    expect(await myMilio.ownerOf(7)).to.equal(recipient.address);
    expect(await myMilio.ownerOf(42)).to.equal(recipient.address);
    expect(await myMilio.tokenURI(7)).to.equal("ipfs://mymilio/7.json");
  });

  it("does not allow the same Abstract deposit to mint twice", async function () {
    const { holder, relayer, recipient, sketchy, abstractBridge, ethereumMinter } =
      await deployFixture();

    await sketchy.connect(holder).setApprovalForAll(await abstractBridge.getAddress(), true);
    const tx = await abstractBridge.connect(holder).bridgeToEthereum([7], recipient.address);
    const receipt = await tx.wait();
    const event = receipt.logs
      .map((log) => {
        try {
          return abstractBridge.interface.parseLog(log);
        } catch {
          return null;
        }
      })
      .find((parsed) => parsed?.name === "BridgeToEthereumInitiated");

    await ethereumMinter.connect(relayer).finalizeBridge(event.args.depositId, recipient.address, [7]);

    await expect(
      ethereumMinter.connect(relayer).finalizeBridge(event.args.depositId, recipient.address, [7])
    ).to.be.revertedWith("deposit processed");
  });
});
