// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title ZONGYUAN-ROOT Truth Anchor Contract
 * @notice 可信真值源区块链锚定合约
 * @dev 将Merkle根锚定到区块链，提供不可篡改的时间证明和存在性证明
 *
 * 功能:
 *   - anchor(bytes32 root): 锚定Merkle根
 *   - anchors(root): 查询锚定信息 (区块号/时间/锚定者)
 *   - getAnchorHistory(root): 获取锚定历史
 *   - verify(root, blockNumber): 验证锚定
 *
 * 安全:
 *   - 只有owner可以设置锚定费用
 *   - 锚定记录不可修改不可删除
 *   - 支持多锚定者
 */
contract TruthAnchor {
    // 锚定记录
    struct AnchorRecord {
        uint256 blockNumber;    // 锚定区块号
        uint256 timestamp;      // 锚定时间戳
        address anchorer;       // 锚定者地址
        uint256 anchorCount;    // 该root被锚定的次数
    }

    // Merkle根 -> 最新锚定记录
    mapping(bytes32 => AnchorRecord) public anchors;

    // Merkle根 -> 锚定历史 (所有锚定事件)
    mapping(bytes32 => AnchorRecord[]) public anchorHistory;

    // 合约所有者
    address public owner;

    // 锚定费用 (wei)
    uint256 public anchorFee;

    // 事件
    event Anchored(
        bytes32 indexed merkleRoot,
        address indexed anchorer,
        uint256 blockNumber,
        uint256 timestamp,
        uint256 anchorCount
    );

    event FeeUpdated(uint256 oldFee, uint256 newFee);
    event OwnershipTransferred(address indexed oldOwner, address indexed newOwner);

    modifier onlyOwner() {
        require(msg.sender == owner, "TruthAnchor: not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        anchorFee = 0; // 默认免费
    }

    /**
     * @notice 锚定Merkle根
     * @param merkleRoot 要锚定的Merkle根哈希
     */
    function anchor(bytes32 merkleRoot) external payable {
        require(msg.value >= anchorFee, "TruthAnchor: insufficient fee");

        AnchorRecord storage existing = anchors[merkleRoot];
        uint256 newCount = existing.anchorCount + 1;

        AnchorRecord memory record = AnchorRecord({
            blockNumber: block.number,
            timestamp: block.timestamp,
            anchorer: msg.sender,
            anchorCount: newCount
        });

        anchors[merkleRoot] = record;
        anchorHistory[merkleRoot].push(record);

        emit Anchored(merkleRoot, msg.sender, block.number, block.timestamp, newCount);

        // 退还多余费用
        if (msg.value > anchorFee) {
            payable(msg.sender).transfer(msg.value - anchorFee);
        }
    }

    /**
     * @notice 批量锚定多个Merkle根
     * @param merkleRoots Merkle根数组
     */
    function anchorBatch(bytes32[] calldata merkleRoots) external payable {
        uint256 totalFee = anchorFee * merkleRoots.length;
        require(msg.value >= totalFee, "TruthAnchor: insufficient fee");

        for (uint256 i = 0; i < merkleRoots.length; i++) {
            bytes32 root = merkleRoots[i];
            AnchorRecord storage existing = anchors[root];
            uint256 newCount = existing.anchorCount + 1;

            AnchorRecord memory record = AnchorRecord({
                blockNumber: block.number,
                timestamp: block.timestamp,
                anchorer: msg.sender,
                anchorCount: newCount
            });

            anchors[root] = record;
            anchorHistory[root].push(record);

            emit Anchored(root, msg.sender, block.number, block.timestamp, newCount);
        }

        if (msg.value > totalFee) {
            payable(msg.sender).transfer(msg.value - totalFee);
        }
    }

    /**
     * @notice 验证Merkle根是否在指定区块号之前被锚定
     * @param merkleRoot Merkle根
     * @param blockNumber 区块号阈值
     * @return bool 是否在指定区块号之前被锚定
     */
    function verify(bytes32 merkleRoot, uint256 blockNumber) external view returns (bool) {
        AnchorRecord memory record = anchors[merkleRoot];
        return record.anchorCount > 0 && record.blockNumber <= blockNumber;
    }

    /**
     * @notice 获取锚定信息
     * @param merkleRoot Merkle根
     * @return blockNumber 区块号
     * @return timestamp 时间戳
     * @return anchorer 锚定者
     * @return anchorCount 锚定次数
     */
    function getAnchor(bytes32 merkleRoot) external view returns (
        uint256 blockNumber,
        uint256 timestamp,
        address anchorer,
        uint256 anchorCount
    ) {
        AnchorRecord memory record = anchors[merkleRoot];
        return (record.blockNumber, record.timestamp, record.anchorer, record.anchorCount);
    }

    /**
     * @notice 获取锚定历史长度
     * @param merkleRoot Merkle根
     * @return 历史记录数
     */
    function getAnchorHistoryLength(bytes32 merkleRoot) external view returns (uint256) {
        return anchorHistory[merkleRoot].length;
    }

    /**
     * @notice 获取指定索引的锚定历史记录
     * @param merkleRoot Merkle根
     * @param index 索引
     * @return 锚定记录
     */
    function getAnchorHistoryEntry(bytes32 merkleRoot, uint256 index) external view returns (
        uint256 blockNumber,
        uint256 timestamp,
        address anchorer,
        uint256 anchorCount
    ) {
        AnchorRecord memory record = anchorHistory[merkleRoot][index];
        return (record.blockNumber, record.timestamp, record.anchorer, record.anchorCount);
    }

    /**
     * @notice 设置锚定费用 (仅owner)
     * @param newFee 新费用 (wei)
     */
    function setAnchorFee(uint256 newFee) external onlyOwner {
        uint256 oldFee = anchorFee;
        anchorFee = newFee;
        emit FeeUpdated(oldFee, newFee);
    }

    /**
     * @notice 转移所有权 (仅owner)
     * @param newOwner 新所有者
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "TruthAnchor: zero address");
        address oldOwner = owner;
        owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }

    /**
     * @notice 提取合约余额 (仅owner)
     */
    function withdraw() external onlyOwner {
        payable(owner).transfer(address(this).balance);
    }
}
