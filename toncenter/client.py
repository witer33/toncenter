import asyncio
import aiohttp
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Optional, Union, List, Any


class GenericException(Exception):
    pass


class ValidationError(GenericException):
    pass


class LiteServerTimeout(GenericException):
    pass


@dataclass_json
@dataclass
class TransactionID:
    lt: Union[int, str]
    hash: str


@dataclass_json
@dataclass
class BlockID:
    workchain: int
    shard: str
    seqno: int
    root_hash: Optional[str] = None
    file_hash: Optional[str] = None


@dataclass_json
@dataclass
class Address:
    account_address: str


@dataclass_json
@dataclass
class FullAccountState:

    balance: Union[int, str]
    last_transaction_id: TransactionID
    block_id: BlockID
    sync_utime: int
    frozen_hash: Optional[str] = None
    data: Optional[str] = None
    code: Optional[str] = None
    address: Optional[Address] = None


@dataclass_json
@dataclass
class WalletState:
    wallet: bool
    balance: Union[int, str]
    account_state: str
    last_transaction_id: TransactionID


@dataclass_json
@dataclass
class MessageData:
    body: str
    init_state: str


@dataclass_json
@dataclass
class Message:
    source: str
    destination: str
    value: Union[str, int]
    fwd_fee: str
    ihr_fee: str
    created_lt: Union[int, str]
    body_hash: str
    msg_data: MessageData
    message: str


@dataclass_json
@dataclass
class Transaction:

    utime: int
    data: str
    transaction_id: TransactionID
    fee: str
    storage_fee: str
    other_fee: str
    in_msg: Message
    out_msgs: List[Message]


@dataclass_json
@dataclass
class Base64Address:

    b64: str
    b64url: str


@dataclass_json
@dataclass
class AddressMetadata:

    raw_form: str
    bounceable: Base64Address
    non_bounceable: Base64Address
    given_type: str
    test_only: bool


@dataclass_json
@dataclass
class MasterchainState:
    last: BlockID
    state_root_hash: str
    init: BlockID


@dataclass_json
@dataclass
class ConsensusBlock:

    consensus_block: int
    timestamp: float


@dataclass_json
@dataclass
class Shards:
    shards: List[BlockID]


@dataclass_json
@dataclass
class ShortTransaction:

    mode: int
    account: str
    lt: Union[int, str]
    hash: str


@dataclass_json
@dataclass
class BlockTransactions:
    id: BlockID
    req_count: int
    incomplete: bool
    transactions: List[ShortTransaction]


@dataclass_json
@dataclass
class BlockHeader:

    id: BlockID
    global_id: int
    version: int
    after_merge: bool
    after_split: bool
    before_split: bool
    want_merge: bool
    want_split: bool
    validator_list_hash_short: int
    catchain_seqno: int
    min_ref_mc_seqno: int
    is_key_block: bool
    prev_key_block_seqno: int
    start_lt: Union[int, str]
    end_lt: Union[int, str]
    prev_blocks: List[BlockID]


class Client:
    def __init__(
        self, token: str = None, base_url: str = "https://toncenter.com/api/v2/"
    ) -> None:
        self.base_url: str = base_url
        self.token: str = token
        self.client: aiohttp.ClientSession = None

    async def start(self) -> None:
        self.client: aiohttp.ClientSession = aiohttp.ClientSession()
        if self.token:
            self.client.headers.update({"X-API-Key": self.token})

    async def close(self) -> None:
        await self.client.close()
    
    async def __aenter__(self) -> "Client":
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def get(self, url: str, params: dict) -> dict:
        async with self.client.get(self.base_url + url, params=params) as response:
            response_json = await response.json()
            if response.status == 200 and response_json["ok"]:
                return response_json["result"]
            elif response.status == 422:
                raise ValidationError(response_json["error"])
            elif response.status == 504:
                raise LiteServerTimeout
            else:
                raise GenericException(response_json["error"])

    async def post(self, url: str, data: dict) -> dict:
        async with self.client.post(self.base_url + url, json=data) as response:
            response_json = await response.json()
            if response.status == 200 and response_json["ok"]:
                return response_json["result"]
            elif response.status == 422:
                raise ValidationError(response_json["error"])
            elif response.status == 504:
                raise LiteServerTimeout
            else:
                raise GenericException(response_json["error"])

    async def get_address_info(self, address: str) -> FullAccountState:
        """
        Get basic information about the address: balance, code, data, last_transaction_id.
        """
        return FullAccountState.from_dict(
            await self.get("getAddressInformation", {"address": address})
        )

    async def get_extended_address_info(self, address: str) -> FullAccountState:
        """
        Similar to previous one but tries to parse additional information for known contract types. 
        This method is based on tonlib's function getAccountState. 
        For detecting wallets we recommend to use getWalletInformation.
        """
        return FullAccountState.from_dict(
            await self.get("getExtendedAddressInformation", {"address": address})
        )

    async def get_wallet_information(self, address: str) -> WalletState:
        """
        Retrieve wallet information. 
        This method parses contract state and currently supports more wallet types than getExtendedAddressInformation: simple wallet, standart wallet, v3 wallet, v4 wallet.
        """
        return WalletState.from_dict(
            await self.get("getWalletInformation", {"address": address})
        )

    async def get_transactions(
        self,
        address: str,
        limit: int = 10,
        lt: int = None,
        hash: str = None,
        to_lt: int = None,
        archival: bool = False,
    ) -> List[Transaction]:
        """
        Get transaction history of a given address.
        """
        params = {
            "address": address,
            "limit": limit,
            "archival": "true" if archival else "false",
        }
        if lt:
            params["lt"] = lt
        if hash:
            params["hash"] = hash
        if to_lt:
            params["to_lt"] = to_lt
        return [
            Transaction.from_dict(transaction)
            for transaction in await self.get("getTransactions", params)
        ]

    async def get_address_balance(self, address: str) -> int:
        """
        Get balance (in nanotons) of a given address.
        """
        return int(await self.get("getAddressBalance", {"address": address}))

    async def get_address_state(self, address: str) -> str:
        """
        Get state of a given address. State can be either unitialized, active or frozen.
        """
        return await self.get("getAddressState", {"address": address})

    async def pack_address(self, address: str) -> str:
        """
        Convert an address from raw to human-readable format.
        """
        return await self.get("packAddress", {"address": address})

    async def unpack_address(self, address: str) -> str:
        """
        Convert an address from human-readable to raw format.
        """
        return await self.get("unpackAddress", {"address": address})

    async def detect_address(self, address: str) -> AddressMetadata:
        """
        Get all possible address forms.
        """
        return AddressMetadata.from_dict(
            await self.get("detectAddress", {"address": address})
        )

    async def get_masterchain_info(self) -> MasterchainState:
        """
        Get up-to-date masterchain state.
        """
        return MasterchainState.from_dict(await self.get("getMasterchainInfo", {}))

    async def get_consensus_block(self) -> ConsensusBlock:
        """
        Get consensus block and its update timestamp.
        """
        return ConsensusBlock.from_dict(await self.get("getConsensusBlock", {}))

    async def lookup_block(
        self,
        workchain: int,
        shard: int,
        seqno: int = None,
        lt: int = None,
        unixtime: int = None,
    ) -> BlockID:
        """
        Look up block by either seqno, lt or unixtime.
        """
        params = {"workchain": workchain, "shard": shard}
        if seqno:
            params["seqno"] = seqno
        if lt:
            params["lt"] = lt
        if unixtime:
            params["unixtime"] = unixtime
        return BlockID.from_dict(await self.get("lookupBlock", params))

    async def get_shards(self, seqno: int) -> Shards:
        """
        Get shards information.
        """
        return Shards.from_dict(await self.get("shards", {"seqno": seqno}))

    async def get_block_transactions(
        self,
        block_id: BlockID,
        after_lt: int = None,
        after_hash: str = None,
        count: int = 40,
    ) -> BlockTransactions:
        """
        Get transactions of the given block.
        """
        params = {
            "workchain": block_id.workchain,
            "shard": block_id.shard,
            "seqno": block_id.seqno,
            "count": count,
        }

        if block_id.root_hash:
            params["root_hash"] = block_id.root_hash
        if block_id.file_hash:
            params["file_hash"] = block_id.file_hash
        if after_lt:
            params["after_lt"] = after_lt
        if after_hash:
            params["after_hash"] = after_hash
        return BlockTransactions.from_dict(
            await self.get("getBlockTransactions", params)
        )

    async def get_block_header(self, block_id: BlockID) -> BlockHeader:
        """
        Get metadata of a given block.
        """
        args = {
            "workchain": block_id.workchain,
            "shard": block_id.shard,
            "seqno": block_id.seqno,
        }
        if block_id.root_hash:
            args["root_hash"] = block_id.root_hash
        if block_id.file_hash:
            args["file_hash"] = block_id.file_hash
        return BlockHeader.from_dict(
            await self.get("getBlockHeader", args)
        )
    
    async def try_locate_transaction(self, source: str, destination: str, created_lt: int) -> Transaction:
        """
        Locate outcoming transaction of destination address by incoming message.
        """
        return Transaction.from_dict(
            await self.get("tryLocateTx", {"source": source, "destination": destination, "created_lt": created_lt})
        )

    async def try_locate_source_transaction(self, source: str, destination: str, created_lt: int) -> Transaction:
        """
        Locate incoming transaction of source address by outcoming message.
        """
        return Transaction.from_dict(
            await self.get("tryLocateSourceTx", {"source": source, "destination": destination, "created_lt": created_lt})
        )
    
    async def run_get_method(self, address: str, method: str, stack: List[Any]) -> dict:
        """
        Run get method on smart contract.
        """
        return await self.post("runGetMethod", {"address": address, "method": method, "stack": stack})
    
    async def send_boc(self, boc: dict) -> dict:
        """
        Send serialized boc file: fully packed and serialized external message to blockchain.
        """
        return await self.post("sendBoc", {"boc": boc})
    
    async def send_query(self, address: str, body: str, init_code: Any = "", init_data: Any = "") -> dict:
        """
        Send query - unpacked external message. This method takes address, body and init-params (if any), packs it to external message and sends to network. All params should be boc-serialized.
        """
        return await self.post("sendQuery", {"address": address, "body": body, "init_code": init_code, "init_data": init_data})
    
    async def estimate_fee(self, address: str, body: str, init_code: Any = "", init_data: Any = "", ignore_chksig: bool = True) -> dict:
        """
        Estimate fees required for query processing. body, init-code and init-data accepted in serialized format (b64-encoded).
        """
        return await self.post("estimateFee", {"address": address, "body": body, "init_code": init_code, "init_data": init_data, "ignore_chksig": ignore_chksig})