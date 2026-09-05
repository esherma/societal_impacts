"""
Phase 0/1 — candidate facilitator addresses on Base.

Sources (see notes/PHASE0_DATA_PATH.md for the full discussion):
  - "onchain_label": BaseScan/Blockscout name tag explicitly identifying the
    address as an x402 facilitator. Highest confidence.
  - "x402_watch": community registry at https://facilitators.x402.watch/,
    fetched 2026-09-05. Self-reported, not verified by us at the source —
    every address here is re-checked for real on-chain activity by
    01_verify_facilitators.py before being trusted.

Do not add addresses here without a source. Do not guess.
"""

FACILITATOR_CANDIDATES = [
    # name, address, source, chain
    ("Coinbase CDP", "0xdbdf3d8ed80f84c35d01c6c9f9271761bad90ba6", "onchain_label", "base"),
    ("Coinbase CDP", "0x9aae2b0d1b9dc55ac9bab9556f9a26cb64995fb9", "x402_watch", "base"),
    ("Coinbase CDP", "0x3a70788150c7645a21b95b7062ab1784d3cc2104", "x402_watch", "base"),
    ("Coinbase CDP", "0x708e57b6650a9a741ab39cae1969ea1d2d10eca1", "x402_watch", "base"),
    ("Coinbase CDP", "0xce82eeec8e98e443ec34fda3c3e999cbe4cb6ac2", "x402_watch", "base"),
    ("Coinbase CDP", "0x7f6d822467df2a85f792d4508c5722ade96be056", "x402_watch", "base"),
    ("Coinbase CDP", "0x001ddabba5782ee48842318bd9ff4008647c8d9c", "x402_watch", "base"),
    ("Coinbase CDP", "0x9c09faa49c4235a09677159ff14f17498ac48738", "x402_watch", "base"),
    ("Coinbase CDP", "0xcbb10c30a9a72fae9232f41cbbd566a097b4e03a", "x402_watch", "base"),
    ("Coinbase CDP", "0x9fb2714af0a84816f5c6322884f2907e33946b88", "x402_watch", "base"),
    ("Questflow", "0x724efafb051f17ae824afcdf3c0368ae312da264", "x402_watch", "base"),
    ("Questflow", "0xa9a54ef09fc8b86bc747cec6ef8d6e81c38c6180", "x402_watch", "base"),
    ("Questflow", "0x4638bc811c93bf5e60deed32325e93505f681576", "x402_watch", "base"),
    ("Questflow", "0xd7d91a42dfadd906c5b9ccde7226d28251e4cd0f", "x402_watch", "base"),
    ("Questflow", "0x4544b535938b67d2a410a98a7e3b0f8f68921ca7", "x402_watch", "base"),
    ("Questflow", "0x59e8014a3b884392fbb679fe461da07b18c1ff81", "x402_watch", "base"),
    ("Questflow", "0xe6123e6b389751c5f7e9349f3d626b105c1fe618", "x402_watch", "base"),
    ("Questflow", "0xf70e7cb30b132fab2a0a5e80d41861aa133ea21b", "x402_watch", "base"),
    ("Questflow", "0x90da501fdbec74bb0549100967eb221fed79c99b", "x402_watch", "base"),
    ("Questflow", "0xce7819f0b0b871733c933d1f486533bab95ec47b", "x402_watch", "base"),
    ("Heurist", "0xb578b7db22581507d62bdbeb85e06acd1be09e11", "x402_watch", "base"),
    ("Heurist", "0x021cc47adeca6673def958e324ca38023b80a5be", "x402_watch", "base"),
    ("Heurist", "0x3f61093f61817b29d9556d3b092e67746af8cdfd", "x402_watch", "base"),
    ("Heurist", "0x290d8b8edcafb25042725cb9e78bcac36b8865f8", "x402_watch", "base"),
    ("Heurist", "0x612d72dc8402bba997c61aa82ce718ea23b2df5d", "x402_watch", "base"),
    ("Heurist", "0x1fc230ee3c13d0d520d49360a967dbd1555c8326", "x402_watch", "base"),
    ("Heurist", "0x48ab4b0af4ddc2f666a3fcc43666c793889787a3", "x402_watch", "base"),
    ("Heurist", "0xd97c12726dcf994797c981d31cfb243d231189fb", "x402_watch", "base"),
    ("Heurist", "0x90d5e567017f6c696f1916f4365dd79985fce50f", "x402_watch", "base"),
    ("X402rs", "0xd8dfc729cbd05381647eb5540d756f4f8ad63eec", "x402_watch", "base"),
    ("X402rs", "0x76eee8f0acabd6b49f1cc4e9656a0c8892f3332e", "x402_watch", "base"),
    ("X402rs", "0x97d38aa5de015245dcca76305b53abe6da25f6a5", "x402_watch", "base"),
    ("X402rs", "0x0168f80e035ea68b191faf9bfc12778c87d92008", "x402_watch", "base"),
    ("X402rs", "0x5e437bee4321db862ac57085ea5eb97199c0ccc5", "x402_watch", "base"),
    ("X402rs", "0xc19829b32324f116ee7f80d193f99e445968499a", "x402_watch", "base"),
    ("PayAI", "0xc6699d2aada6c36dfea5c248dd70f9cb0235cb63", "x402_watch", "base"),
    ("PayAI", "0xb2bd29925cbbcea7628279c91945ca5b98bf371b", "x402_watch", "base"),
    ("PayAI", "0x25659315106580ce2a787ceec5efb2d347b539c9", "x402_watch", "base"),
    ("PayAI", "0xb8f41cb13b1f213da1e94e1b742ec1323235c48f", "x402_watch", "base"),
    ("PayAI", "0xe575fa51af90957d66fab6d63355f1ed021b887b", "x402_watch", "base"),
    ("CodeNut", "0x8d8Fa42584a727488eeb0E29405AD794a105bb9b", "x402_watch", "base"),
    ("CodeNut", "0x87aF99356d774312B73018b3B6562e1aE0e018C9", "x402_watch", "base"),
    ("CodeNut", "0x65058CF664D0D07f68B663B0D4b4f12A5E331a38", "x402_watch", "base"),
    ("CodeNut", "0x88E13D4c764a6c840Ce722A0a3765f55A85b327E", "x402_watch", "base"),
    ("AurraCloud", "0x222c4367a2950f3b53af260e111fc3060b0983ff", "x402_watch", "base"),
    ("AurraCloud", "0xb70c4fe126de09bd292fe3d1e40c6d264ca6a52a", "x402_watch", "base"),
    ("AurraCloud", "0xd348e724e0ef36291a28dfeccf692399b0e179f8", "x402_watch", "base"),
    ("OpenX402", "0x97316fa4730bc7d3b295234f8e4d04a0a4c093e8", "x402_watch", "base"),
    ("OpenX402", "0x97db9b5291a218fc77198c285cefdc943ef74917", "x402_watch", "base"),
    ("KAMIYO", "0x742d35cc6634c0532925a3b844bc9e7595f0bee4", "x402_watch", "base"),
    ("Thirdweb", "0x80c08de1a05df2bd633cf520754e40fde3c794d3", "x402_watch", "base"),
    ("Daydreams", "0x279e08f711182c79Ba6d09669127a426228a4653", "x402_watch", "base"),
    ("Ultravioleta DAO", "0x103040545ac5031a11e8c03dd11324c7333a13c7", "x402_watch", "base"),
    ("Mogami", "0xfe0920a0a7f0f8a1ec689146c30c3bbef439bf8a", "x402_watch", "base"),
    ("402104", "0x73b2b8df52fbe7c40fe78db52e3dffdd5db5ad07", "x402_watch", "base"),
    ("xEcho", "0x3be45f576696a2fd5a93c1330cd19f1607ab311d", "x402_watch", "base"),
    ("Virtuals Protocol", "0x80735b3f7808e2e229ace880dbe85e80115631ca", "x402_watch", "base"),
]

USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
AUTHORIZATION_USED_TOPIC = "0x98de503528ee59b575ef0c0a2576a82497bfc029a5685b209e9ec333479b10a5"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

if __name__ == "__main__":
    base_only = [c for c in FACILITATOR_CANDIDATES if c[3] == "base"]
    print(f"{len(FACILITATOR_CANDIDATES)} total candidates, {len(base_only)} on Base")
