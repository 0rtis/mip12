
# Mochimo Improvement Proposal #12

This proposal main goal is to implement decentralized application on the Mochimo blockchain.

Some change included in this proposal are provided along with *Proof Of Concept* (POC) implementation in Python that should help the reviewers understanding the technical aspects of the proposed change.
Other are marked as tentative either because the technical solution is still unclear or because the implementation is complex and might be delivered in a future MIP.

## MIP12A - Block time & size
We propose to reduce the block time from 337.5 seconds (256 block/day) to 42.1875 seconds (2048 block/day).
This will improve the overall user experience. The cost of this change is two folds:
1. Increased syncing time: up to 2047 x 2 block trailer might be downloaded for syncing instead of 255 x 2.
   However, considering the small size of a block trailer, the impact should be limited
2. Reduced timeframe for block propagation: each block must propagate within 42 seconds instead of 337 seconds.
   Therefore, we propose to change the max block size to 1Mb, which should be enough to safely propagate a block to all node within the timeframe


## MIP12B - Signature
We propose to move to a Signature agnostic model

### MIP12B1 - Hash based WOTS
We propose to implement a hash based WOTS scheme where the internal ledger stores a hash of the public key instead of the raw public key

### MIP12B2 - Falcon
We propose to implement [Falcon](https://falcon-sign.info/)

## MIP12C - Json RPC
We propose to move away from the raw binary RPC to a JSON one for all network communication. Raw binary do not integrate well in a web environment nor with recent technical stacks.
Providing a Json based RPC would help developer to build on and integrate Mochimo in their ecosystem.
Note that this feature will effectively turn all node into APIs

## MIP12D - Wallets
We propose to facilitate user onboarding by providing multiple wallets

### MIP12D1 - Chrome extension wallet
We propose to implement a Chrome extension wallet that would levelrage the existing Javascript port of Mochimo routines.

### MIP12D2 - Wallet Connect
*Tentative. Expected feasibility: medium*
We propose to integrate [Wallet Connect](https://walletconnect.com/) into a Mochimo app for smartphone.
Wallet Connect is a blockchain agnostic wallet that act as a middle man between a wallet and a decentralized application.
The Wallet Connect protocol does not require the user to disclose its private key to any third party.

## MIP12E - On-chain applications

We propose to implement on-chain applications.

### Not another EVM
The leading on-chain computation engine is the Ethereum Virtual Machine (EVM). It is used on the vast majority of smart-contract blockchains.
We believe the EVM market to be saturated. Mochimo must distinguish itself by proposing something different.
The EVM offers developers total freedom when building applications. However, this freedom come with major costs:
1. Low code quality have led to billions of value lost
2. Poorly designed token standard duplicate data and causing rapid increase in storage requirements
3. Unsustainable storage model: pay once, stored forever
4. Unlimited amounts of useless copycat app & shitcoin. Do we really need 50 version of Uniswap and 200 meme coins ?

We propose to implement Application Template, Application Instance and the Mochimo Application Machine

### Application Template, Application Instance and the Mochimo Application Machine

An Application Template is a set of function defined *natively within the Mochimo node source code*.
Because they are part of the node source code, new Application Template can only be created through a hardfork.

An Application Instance is similar to a smart contract: it exists on-chain with its own set of parameters and storage.
Application Instance are unique and create from an Application Template through a governance event (see govenance section).
There could be several Application Instance created from the same Application Template.

The Mochimo Application Machine is akin to the EVM: it executes a set of instruction defined by the Application Template functions originated from the target Application Instance.
Each instruction cost *gas* and the total *gas* used at the end of the execution is paid to the miner at the rate of *gas_price*

### MIP12E1 - Storage rent
Because applications requires storage, we propose to implement a rent for user data storage. The rent is charged each Neo Genesis block and is based on the size of the storage used by each address.
The rent is paid in MCM. Storage used by application (data specific to the application, not user data) is free.

### MIP12E2 - Asset application
We propose to implement an asset application to create and manage assets on-chain (token, NFT, etc).
The creation of an asset is triggered by a governance event

### MIP12E3 - Escrow/Marketplace application
We propose to implement an application for on-chain barter

### MIP12E4 - Automated Market Making (DEx) application
We propose to implement an application to trade fungible assets on-chain (similar to Uniswap)

### MIP12E5 - Messaging application
We propose to implement an application to send message on-chain.
Message are limited in size and follow an exponentially increasing cost per byte.
Only on message per user at most is stored on-chain.
This would allow pseudo anonymous communication but would also permit to use Mochimo as a communication layer for third party application

### MIP12E6 - Smart account application
*Tentative. Expected feasibility: easy*

We propose to implement a smart account application that will provide various feature such as:
1. Multisig
2. Limit spending
3. Freeze
4. Social Recovery
5. Dead Man Switch/Will Execution

### MIP12E7 - Governance and Staking application
*Tentative. Expected feasibility: hard*

We propose to introduce an on-chain governance & treasury funded by a share of the fee generated by the applications & storage rent.

We propose implement an application for staking MCM. Staked MCM are locked for a fixed amount of time/block.
Stakers are able to earn a share of the fee generated by the applications & storage rent and vote on governance proposals.
Proposals supported by more than 50% of the total staked are executed on-chain on the following Neo Genesis block.

### Governance
Each staked MCM give the user the right to vote on proposal (ex: creation of a new Application Instance, payment from treasury, etc)
There is two different possible approach to proposal submission:
1. Any staker can submit a proposal by putting up a collateral in MCM. If the proposal reaches a certain participation threshold, the collateral is returned. This is to prevent spamming (additional limitation suck as hard limit might be required).
2. Only the Governance Committee (on-chain application) can submit a proposal. Committee members could be Dev Team, Founders, mining pool, etc

In all cases, a proposal is only executed if there is enough support vote by the stakers

### Staking rewards
Staking rewards are calculated using the [MasterChef algorithm](https://github.com/pancakeswap/pancake-farm/blob/master/contracts/MasterChef.sol#L229).
The complexity of this algorithm is **O(1)** and well suited for on-chain computation

### MIP12E8 - Bridge application
*Tentative. Expected feasibility: very hard*

We propose to implement a bridge application to allow the transfer of asset to and from the Mochimo network.

Several approach are available:
1. Use a thrid party: https://layerzero.network/ https://allbridge.io/ https://www.synapseprotocol.com/ https://wormhole.com/
2. Use a side chain: the side chain is made of N nodes. To bridge in, the nodes minotr deposits on the EVM smart contract and mint assets on Mochimo after confirmation. To bridge out, the N node sign an EVM transaction to send tokens to the destination address. N must be kept to a small number (~=100)
3. Leverage existing research to build a native bridge: https://arxiv.org/pdf/2102.04660.pdf https://arxiv.org/pdf/2101.06000v1.pdf https://arxiv.org/pdf/2210.00264.pdf https://near.org/blog/eth-near-rainbow-bridge https://github.com/crossclaim

### MIP12E9 - Privacy bond
*Tentative. Expected feasibility: hard*

We propose to implement a privacy application that will generate MCM bonds without any link to a specific user (Ring Signature, Stealth Address)

