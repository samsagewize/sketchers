import { expect } from "chai";
import hre from "hardhat";

const { ethers, network } = hre;

describe("Milio staking rewards", function () {
  async function deployFixture(rewardRate = ethers.parseEther("1")) {
    const [admin, holder, other] = await ethers.getSigners();

    const MyMilio = await ethers.getContractFactory("MyMilio");
    const myMilio = await MyMilio.deploy(admin.address, "ipfs://mymilio/");
    await myMilio.waitForDeployment();

    const MilioToken = await ethers.getContractFactory("MilioToken");
    const milio = await MilioToken.deploy(admin.address);
    await milio.waitForDeployment();

    const Staking = await ethers.getContractFactory("MyMilioStaking");
    const staking = await Staking.deploy(
      admin.address,
      await myMilio.getAddress(),
      await milio.getAddress(),
      rewardRate
    );
    await staking.waitForDeployment();

    await milio.grantRole(await milio.MINTER_ROLE(), await staking.getAddress());
    await myMilio.mintFromBridge(holder.address, 1, ethers.id("deposit-1"));
    await myMilio.mintFromBridge(holder.address, 2, ethers.id("deposit-2"));

    return { admin, holder, other, myMilio, milio, staking };
  }

  it("has a fixed 21 million max supply and no premint", async function () {
    const { milio } = await deployFixture();

    expect(await milio.name()).to.equal("Milio");
    expect(await milio.symbol()).to.equal("MILIO");
    expect(await milio.cap()).to.equal(ethers.parseEther("21000000"));
    expect(await milio.totalSupply()).to.equal(0n);
  });

  it("stakes MyMilios and mints MILIO rewards over time", async function () {
    const { holder, myMilio, milio, staking } = await deployFixture();

    await myMilio.connect(holder).setApprovalForAll(await staking.getAddress(), true);
    await staking.connect(holder).stake([1]);

    expect(await myMilio.ownerOf(1)).to.equal(await staking.getAddress());
    expect(await staking.stakedBalance(holder.address)).to.equal(1n);

    await network.provider.send("evm_increaseTime", [10]);
    await network.provider.send("evm_mine");

    await staking.connect(holder).claim([1]);
    expect(await milio.balanceOf(holder.address)).to.equal(ethers.parseEther("11"));
  });

  it("unlocks the NFT and claims pending rewards on unstake", async function () {
    const { holder, myMilio, milio, staking } = await deployFixture();

    await myMilio.connect(holder).setApprovalForAll(await staking.getAddress(), true);
    await staking.connect(holder).stake([1]);

    await network.provider.send("evm_increaseTime", [5]);
    await network.provider.send("evm_mine");

    await staking.connect(holder).unstake([1]);

    expect(await myMilio.ownerOf(1)).to.equal(holder.address);
    expect(await staking.stakedBalance(holder.address)).to.equal(0n);
    expect(await milio.balanceOf(holder.address)).to.be.greaterThan(0n);
  });

  it("does not let another wallet claim or unstake someone else's NFT", async function () {
    const { holder, other, myMilio, staking } = await deployFixture();

    await myMilio.connect(holder).setApprovalForAll(await staking.getAddress(), true);
    await staking.connect(holder).stake([1]);

    await expect(staking.connect(other).claim([1])).to.be.revertedWith("not staker");
    await expect(staking.connect(other).unstake([1])).to.be.revertedWith("not staker");
  });

  it("caps staking mints at 21 million MILIO", async function () {
    const { holder, myMilio, milio, staking } = await deployFixture(ethers.parseEther("30000000"));

    await myMilio.connect(holder).setApprovalForAll(await staking.getAddress(), true);
    await staking.connect(holder).stake([1]);

    await network.provider.send("evm_increaseTime", [1]);
    await network.provider.send("evm_mine");

    await staking.connect(holder).claim([1]);
    expect(await milio.totalSupply()).to.equal(await milio.cap());
    expect(await milio.balanceOf(holder.address)).to.equal(await milio.cap());
  });

  it("rejects unrelated NFTs sent directly to staking", async function () {
    const { holder, staking } = await deployFixture();
    const MockSketchyMilio = await ethers.getContractFactory("MockSketchyMilio");
    const unrelated = await MockSketchyMilio.deploy();
    await unrelated.waitForDeployment();

    await unrelated.mint(holder.address, 77);

    await expect(
      unrelated
        .connect(holder)
        ["safeTransferFrom(address,address,uint256)"](
          holder.address,
          await staking.getAddress(),
          77
        )
    ).to.be.revertedWith("unsupported nft");
  });
});
