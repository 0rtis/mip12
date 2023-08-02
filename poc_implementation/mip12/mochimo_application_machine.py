import math
import traceback
from typing import List, Dict, Union, Literal

from poc_implementation.mip12.application import ApplicationTemplate, ApplicationInstance
from poc_implementation.mip12.storage import Storage
from poc_implementation.mip12.blockchain import Blockchain
from poc_implementation.mip12.execution_context import ExecutionContext


INT_ENCODING: Literal['big', 'little'] = "big"
STR_ENCODING = "utf-8"
DECIMAL_SCALE = 10000
APP_INSTANCE_ID_LENGTH = 4

BNUM_LENGTH = 8
DATA_LENGTH = 8

APP_TEMPLATE_TYPE_MCM = 0
APP_TEMPLATE_TYPE_ASSETS = 1
APP_TEMPLATE_TYPE_AMM = 2
APP_TEMPLATE_TYPE_MARKETPLACE = 3
APP_TEMPLATE_TYPE_CHAT = 5

MCM_APP_ID = 0

GAS_PRICE = 3


class MCM(ApplicationInstance):
    BALANCE_LENGTH = 8

    def __init__(self):
        self.instance_address = None
        self.instance_id = MCM_APP_ID
        self.max_storage = 0

    def init(self, instance_id: int, instance_address: bytes) -> 'ApplicationInstance':
        self.instance_id = instance_id
        self.instance_address = instance_address
        return self

    def get_instance_address(self) -> bytes:
        return self.instance_address

    def get_instance_id(self) -> int:
        return self.instance_id

    def get_max_storage(self) -> int:
        return self.max_storage

    def execute(self, caller: bytes, function_selector: int, function_param: bytes, execution_context: ExecutionContext):
        if function_selector == 1:  # create_tag(tag)
            execution_context.op(3)
            new_address = function_param[:12]
            execution_context.op(5)
            funding = int.from_bytes(function_param[12:12+MCM.BALANCE_LENGTH], INT_ENCODING)
            execution_context.op(3)
            if funding < 500:
                raise Exception("Not enough funding")

            # substract funding from caller
            caller_account_storage = execution_context.read_account_storage(caller)
            caller_account_array = MAM.parse_array(caller_account_storage, execution_context)
            caller_app_storage, caller_mcm_app_index = MAM.get_app_data_from_array(MCM_APP_ID, caller_account_array, execution_context)
            caller_balance = MCM.get_balance(caller_app_storage, execution_context)
            execution_context.op(2)
            if caller_balance < funding:
                raise Exception("Not enough balance to fund new address")
            caller_app_storage = MCM.subtract_from_balance(caller_app_storage, funding, execution_context)
            caller_account_array[caller_mcm_app_index] = caller_app_storage
            caller_account_storage = MAM.account_array_to_bytes(caller_account_array, execution_context)
            execution_context.write_account_storage(caller, caller_account_storage)

            new_account_storage = execution_context.read_account_storage(new_address)
            execution_context.op(3)
            if len(new_account_storage) > 0:
                raise Exception("Address {} already exists".format(new_address.hex()))

            execution_context.op(4)
            new_account_storage = funding.to_bytes(MCM.BALANCE_LENGTH, INT_ENCODING)
            new_account_storage = self.instance_id.to_bytes(APP_INSTANCE_ID_LENGTH, INT_ENCODING) + len(new_account_storage).to_bytes(DATA_LENGTH, INT_ENCODING) + new_account_storage
            new_account_storage = MAM.account_array_to_bytes([new_account_storage], execution_context)
            execution_context.write_account_storage(new_address, new_account_storage)

            return 0
        elif function_selector == 2:  # transfer([(amount, destination, memo), ...])
            transfers = MAM.parse_array(function_param, execution_context)
            total = 0
            for tx in transfers:
                amount = int.from_bytes(tx[:MCM.BALANCE_LENGTH], INT_ENCODING)
                destination = tx[MCM.BALANCE_LENGTH:MCM.BALANCE_LENGTH+12]
                l = int.from_bytes(tx[MCM.BALANCE_LENGTH+12:MCM.BALANCE_LENGTH+12+DATA_LENGTH], INT_ENCODING)
                if l > 64:
                    raise Exception("Memo is too long")
                memo = tx[MCM.BALANCE_LENGTH+12+DATA_LENGTH:MCM.BALANCE_LENGTH+12+DATA_LENGTH+l]

                # credit amount to destination
                destination_account_storage = execution_context.read_account_storage(destination)
                if len(destination_account_storage) <= 0:
                    raise Exception("Destination {} not found".format(destination.decode(STR_ENCODING)))
                destination_account_array = MAM.parse_array(destination_account_storage, execution_context)
                destination_app_storage, destination_mcm_app_index = MAM.get_app_data_from_array(MCM_APP_ID, destination_account_array, execution_context)
                destination_app_storage = MCM.add_to_balance(destination_app_storage, amount, execution_context)
                MAM.set_to_array(destination_app_storage, destination_account_array, destination_mcm_app_index)
                destination_account_storage = MAM.array_to_bytes(destination_account_array, execution_context)
                execution_context.write_account_storage(destination, destination_account_storage)

            # subtract total from caller
            caller_account_storage = execution_context.read_account_storage(caller)
            caller_account_array = MAM.parse_array(caller_account_storage, execution_context)
            caller_app_storage, caller_mcm_app_index = MAM.get_app_data_from_array(MCM_APP_ID, caller_account_array, execution_context)
            caller_balance = MCM.get_balance(caller_app_storage, execution_context)
            execution_context.op(2)
            if caller_balance < total:
                raise Exception("Not enough balance")
            caller_app_storage = MCM.subtract_from_balance(caller_app_storage, total, execution_context)
            caller_account_array[caller_mcm_app_index] = caller_app_storage
            caller_account_storage = MAM.account_array_to_bytes(caller_account_array, execution_context)
            execution_context.write_account_storage(caller, caller_account_storage)
        else:
            raise Exception("No such method")

    @staticmethod
    def get_balance(app_account_data: bytes, execution_context: ExecutionContext = ExecutionContext.no_op()) -> int:
        execution_context.op(1)
        execution_context.op(6)
        return int.from_bytes(app_account_data[APP_INSTANCE_ID_LENGTH + DATA_LENGTH:APP_INSTANCE_ID_LENGTH+DATA_LENGTH+MCM.BALANCE_LENGTH], INT_ENCODING)

    @staticmethod
    def subtract_from_balance(app_account_data: bytes, amount: int, execution_context: ExecutionContext = ExecutionContext.no_op()) -> bytes:
        execution_context.op(1)
        _copy = bytearray(app_account_data)
        execution_context.op(1)
        balance = MCM.get_balance(_copy)
        execution_context.op(2)
        balance -= amount
        if balance < 0:
            raise Exception("Negative balance")
        execution_context.op(6)
        _copy[APP_INSTANCE_ID_LENGTH+DATA_LENGTH:APP_INSTANCE_ID_LENGTH+DATA_LENGTH+MCM.BALANCE_LENGTH] = balance.to_bytes(MCM.BALANCE_LENGTH, INT_ENCODING)
        return bytes(_copy)

    @staticmethod
    def add_to_balance(app_account_data: bytes, amount: int, execution_context: ExecutionContext = ExecutionContext.no_op()) -> bytes:
        execution_context.op(1)
        _copy = bytearray(app_account_data)
        execution_context.op(1)
        balance = MCM.get_balance(_copy)
        execution_context.op(2)
        balance += amount
        execution_context.op(6)
        _copy[APP_INSTANCE_ID_LENGTH + DATA_LENGTH:APP_INSTANCE_ID_LENGTH + DATA_LENGTH + MCM.BALANCE_LENGTH] = balance.to_bytes(MCM.BALANCE_LENGTH, INT_ENCODING)
        return bytes(_copy)

    @staticmethod
    def set_balance(app_account_data: bytes, balance: int, execution_context: ExecutionContext = ExecutionContext.no_op()) -> bytes:
        execution_context.op(1)
        _copy = bytearray(app_account_data)
        execution_context.op(6)
        _copy[APP_INSTANCE_ID_LENGTH + DATA_LENGTH:APP_INSTANCE_ID_LENGTH + DATA_LENGTH + MCM.BALANCE_LENGTH] = balance.to_bytes(MCM.BALANCE_LENGTH, INT_ENCODING)
        return bytes(_copy)


class Assets(ApplicationInstance):
    """
    Internal storage: [(symbol, total supply, options)]
    """

    TYPE_FUNGIBLE = 1
    TYPE_NON_FUNGIBLE = 2
    MODE_NOT_MINTABLE = 1

    SYMBOL_LENGTH = 4

    def __init__(self):
        self.instance_address = None
        self.instance_id = None
        self.max_storage = 128 * 1024 * 1024

    def init(self, instance_id: int, instance_address: bytes) -> 'ApplicationInstance':
        self.instance_id = instance_id
        self.instance_address = instance_address
        return self

    def get_instance_address(self) -> bytes:
        return self.instance_address

    def get_instance_id(self) -> int:
        return self.instance_id

    def get_max_storage(self) -> int:
        return self.max_storage

    def execute(self, caller: bytes, function_selector: int, function_param: bytes, execution_context: ExecutionContext):
        if function_selector == 1:  # create(symbol, type, admin, modes, data)
            app_storage = execution_context.read_app_storage(self.instance_id)
            app_array = MAM.parse_array(app_storage, execution_context)
            tokens_info = Assets.app_array_to_tokens_info(app_array)
            new_token = Assets.get_token_info(function_param)

            if new_token[0] in tokens_info:
                raise Exception("Token already exists")

            if new_token[1] == Assets.TYPE_FUNGIBLE:
                if new_token[4][0] != 0:
                    raise Exception("Total supply must be 0")
                if new_token[4][1] > 18:
                    raise Exception("Decimal cannot be grater than 18")

                app_array.append(function_param)
                app_storage = MAM.array_to_bytes(app_array, execution_context)
                execution_context.write_app_storage(self.instance_id, app_storage)
            elif new_token[1] == Assets.TYPE_NON_FUNGIBLE:
                raise Exception("Not implemented")
            else:
                raise Exception("Unhandled token type")
        elif function_selector == 2:  # mint([(symbol, [(value, recipient), ...]), ...]) value cant be amount of NFT id
            offset = 0
            symbol = function_param[offset:offset+Assets.SYMBOL_LENGTH].decode(STR_ENCODING)
            offset += Assets.SYMBOL_LENGTH
            mint_list = MAM.parse_array(function_param[offset:])

            asset_storage = execution_context.read_app_storage(self.instance_id)
            app_array = MAM.parse_array(asset_storage, execution_context)
            tokens_info = Assets.app_array_to_tokens_info(app_array)

            if symbol not in tokens_info:
                raise Exception("Symbol {} not found".format(symbol))
            token_info = tokens_info[symbol]
            if not Assets.is_mintable(caller, token_info):
                raise Exception("Not mintable")

            for mint in mint_list:
                offset = 0
                l = int.from_bytes(mint[offset:offset+DATA_LENGTH], INT_ENCODING)
                offset += DATA_LENGTH
                amount = int.from_bytes(mint[offset:offset + l], INT_ENCODING)
                offset += l
                recipient = mint[offset:offset+12]
                recipient_storage = execution_context.read_account_storage(recipient)
                recipient_array = MAM.parse_array(recipient_storage, execution_context)
                recipient_asset_storage, recipient_asset_index = MAM.get_app_data_from_array(self.instance_id, recipient_array, execution_context)
                recipient_asset_storage = Assets.update_balance(self.instance_id, recipient_asset_storage, symbol, token_info[1], amount, execution_context)
                MAM.set_to_array(recipient_asset_storage, recipient_array, recipient_asset_index, execution_context)
                recipient_storage = MAM.account_array_to_bytes(recipient_array, execution_context)
                execution_context.write_account_storage(recipient, recipient_storage)

            return 0
        elif function_selector == 3:  # transfer([(symbol, value, recipient), ...] value cant be amount of NFT id
            token_params = MAM.parse_array(function_param)
            asset_storage = execution_context.read_app_storage(self.instance_id)
            app_array = MAM.parse_array(asset_storage, execution_context)
            tokens_info = Assets.app_array_to_tokens_info(app_array)

            for tp in token_params:
                symbol = tp[:Assets.SYMBOL_LENGTH].decode()
                if symbol not in tokens_info:
                    raise Exception("Symbol {} not found".format(symbol))
                token_info = tokens_info[symbol]
                offset = Assets.SYMBOL_LENGTH
                l = int.from_bytes(tp[offset:offset + DATA_LENGTH], INT_ENCODING)
                offset += DATA_LENGTH
                amount = int.from_bytes(tp[offset:offset+l], INT_ENCODING)
                offset += l
                if amount == 0:
                    continue
                recipient = tp[offset:offset+12]

                caller_storage = execution_context.read_account_storage(caller)
                caller_array = MAM.parse_array(caller_storage, execution_context)
                caller_asset_storage, caller_asset_index = MAM.get_app_data_from_array(self.instance_id, caller_array, execution_context)
                if caller_asset_index < 0:
                    raise Exception("Caller's storage of token {} is empty".format(symbol))
                caller_asset_storage = Assets.update_balance(self.instance_id, caller_asset_storage, symbol, token_info[1], -amount, execution_context)
                caller_array[caller_asset_index] = caller_asset_storage
                caller_storage = MAM.account_array_to_bytes(caller_array, execution_context)
                execution_context.write_account_storage(caller, caller_storage)

                recipient_storage = execution_context.read_account_storage(recipient)
                recipient_array = MAM.parse_array(recipient_storage, execution_context)
                recipient_asset_storage, recipient_asset_index = MAM.get_app_data_from_array(self.instance_id, recipient_array, execution_context)
                recipient_asset_storage = Assets.update_balance(self.instance_id, recipient_asset_storage, symbol, token_info[1], amount, execution_context)
                MAM.set_to_array(recipient_asset_storage, recipient_array, recipient_asset_index, execution_context)
                recipient_storage = MAM.account_array_to_bytes(recipient_array, execution_context)
                execution_context.write_account_storage(recipient, recipient_storage)
        elif function_selector == 4:  # setAdmin(symbol, new_admin_address)
            raise Exception("Not implemented")
        elif function_selector == 5:  # setModes([mode, ...])
            raise Exception("Not implemented")
        else:
            raise Exception("No such method")

    @staticmethod
    def get_token_info(token_storage: bytes):
        """
        (symbol, type, admin, mode, data)
        fungible data: (total supply, decimal)
        :param token_storage:
        :return:
        """
        symbol = token_storage[:Assets.SYMBOL_LENGTH].decode(STR_ENCODING)
        token_type = int(token_storage[Assets.SYMBOL_LENGTH])
        offset = Assets.SYMBOL_LENGTH + 1
        admin = token_storage[offset: offset + 12]
        offset += 12
        modes = []
        l = int(token_storage[offset])
        for i in range(l):
            modes.append(int(token_storage[offset + 1 + i]))
        offset += 1 + l
        l = int.from_bytes(token_storage[offset:offset+DATA_LENGTH], INT_ENCODING)
        offset += DATA_LENGTH

        data = token_storage[offset:offset+l]
        if token_type == Assets.TYPE_FUNGIBLE:
            offset = 0
            l = int.from_bytes(data[offset:offset+DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            total_supply = int.from_bytes(data[offset:offset+l], INT_ENCODING)
            offset += l
            l = int.from_bytes(data[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            decimal = int.from_bytes(data[offset:offset + l], INT_ENCODING)
            data = (total_supply, decimal)
        elif token_type == Assets.TYPE_NON_FUNGIBLE:
            offset = 0
            l = int.from_bytes(data[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            total_supply = int.from_bytes(data[offset:offset + l], INT_ENCODING)
            offset += l
            l = int.from_bytes(data[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            base_url = data[offset:offset + l].decode(STR_ENCODING)
            data = (total_supply, base_url)
        else:
            raise Exception("Unhandled token type")

        return symbol, token_type, admin, modes, data

    @staticmethod
    def app_array_to_tokens_info(app_array: list):
        tokens_info = {}
        for token_storage in app_array:
            token_info = Assets.get_token_info(token_storage)
            assert token_info[0] not in tokens_info
            tokens_info[token_info[0]] = token_info
        return tokens_info

    @staticmethod
    def is_mintable(minter: bytes, token_info: tuple):
        if token_info[1] == Assets.TYPE_FUNGIBLE:
            if token_info[2] == minter:
                return Assets.MODE_NOT_MINTABLE not in token_info[3]
            return False
        elif token_info[1] == Assets.TYPE_NON_FUNGIBLE:
            raise Exception("Not implemented")
        else:
            raise Exception("Unhandled token type")

    @staticmethod
    def get_account_tokens(account_assets_storage: bytes, execution_context: ExecutionContext = ExecutionContext.no_op()) -> dict:
        execution_context.op(1)
        tokens = {}
        if len(account_assets_storage) <= APP_INSTANCE_ID_LENGTH+DATA_LENGTH:
            return tokens
        account_asset_array = MAM.parse_array(account_assets_storage[APP_INSTANCE_ID_LENGTH+DATA_LENGTH:], execution_context)
        for account_asset in account_asset_array:
            execution_context.op(4)
            symbol = account_asset[:Assets.SYMBOL_LENGTH].decode(STR_ENCODING)
            execution_context.op(3)
            token_type = account_asset[Assets.SYMBOL_LENGTH]
            execution_context.op(2)
            offset = Assets.SYMBOL_LENGTH + 1
            data = None
            execution_context.op(2)
            if token_type == Assets.TYPE_FUNGIBLE:
                execution_context.op(5)
                l = int.from_bytes(account_asset[offset:offset+DATA_LENGTH], INT_ENCODING)
                execution_context.op(2)
                offset += DATA_LENGTH
                execution_context.op(5)
                balance = int.from_bytes(account_asset[offset:offset+l], INT_ENCODING)
                execution_context.op(1)
                data = balance
            elif token_type == Assets.TYPE_NON_FUNGIBLE:
                raise Exception("Not implemented")
            else:
                raise Exception("Unhandled token type")
            execution_context.op(2)
            tokens[symbol] = (symbol, token_type, data)

        return tokens

    @staticmethod
    def update_balance(app_instance_id: int, account_app_storage: bytes, symbol: Union[str, bytes], token_type: int, change_amount: int,  execution_context: ExecutionContext = ExecutionContext.no_op()) -> bytes:
        if type(symbol) == str:
            symbol = symbol.encode(STR_ENCODING)
        execution_context.op(3)

        data = None
        execution_context.op(3)

        account_tokens = MAM.parse_array(account_app_storage[APP_INSTANCE_ID_LENGTH+DATA_LENGTH:]) if len(account_app_storage) > 0 else []
        for i in range(len(account_tokens)):
            account_token_storage = account_tokens[i]
            account_token_type = account_token_storage[Assets.SYMBOL_LENGTH]
            if symbol == account_token_storage[:Assets.SYMBOL_LENGTH] and token_type == account_token_type:
                execution_context.op(2)
                offset = Assets.SYMBOL_LENGTH + 1
                if account_token_type == Assets.TYPE_FUNGIBLE:
                    execution_context.op(5)
                    l = int.from_bytes(account_token_storage[offset:offset+DATA_LENGTH], INT_ENCODING)
                    offset += DATA_LENGTH
                    execution_context.op(2)
                    balance = int.from_bytes(account_token_storage[offset:offset+l], INT_ENCODING)
                    balance += change_amount
                    if balance < 0:
                        raise Exception("Invalid amount")
                    execution_context.op(2)
                    if balance == 0:
                        account_tokens.pop(i)
                        i -= 1
                        data = bytes(0)
                    else:
                        data = symbol + int(token_type).to_bytes(1, INT_ENCODING) + MAM.pack_int(balance)
                        execution_context.op(3)
                        account_tokens[i] = data
                    break
                elif account_token_type == Assets.TYPE_NON_FUNGIBLE:
                    raise Exception("Not implemented")
                else:
                    raise Exception("Unhandled token type")

        if data is None:
            # token not found
            if token_type == Assets.TYPE_FUNGIBLE:
                execution_context.op(1)
                balance = change_amount
                execution_context.op(9)
                data = symbol + int(token_type).to_bytes(1, INT_ENCODING) + MAM.pack_int(balance)
                account_tokens.append(data)
            elif token_type == Assets.TYPE_NON_FUNGIBLE:
                raise Exception("Not implemented")
            else:
                raise Exception("Unhandled token type")

            if len(account_app_storage) <= 0:
                # create an entry for asset application
                execution_context.op(3)
                app_storage = MAM.account_array_to_bytes([data])
                return app_instance_id.to_bytes(APP_INSTANCE_ID_LENGTH, INT_ENCODING) + len(app_storage).to_bytes(DATA_LENGTH, INT_ENCODING) + app_storage

        execution_context.op(7)
        array_storage = MAM.array_to_bytes(account_tokens, execution_context)
        return account_app_storage[:APP_INSTANCE_ID_LENGTH] + len(array_storage).to_bytes(DATA_LENGTH, INT_ENCODING) + array_storage


class AMM(ApplicationInstance):
    """
    https://docs.uniswap.org/contracts/v2/concepts/core-concepts/pools
    Internal storage:
    token A symbol + tokenA type + token B symbol + token B type + K length + K + Assets app id
    + fee bps + LP supply length + LP supply + Sum bnum_i length + S bnu,_i
    + token A reserve length + token A reserve + token B reserve length + token B reserve

    """

    def __init__(self):
        self.instance_address = None
        self.instance_id = None
        self.max_storage = 128

    def init(self, instance_id: int, instance_address: bytes) -> 'ApplicationInstance':
        self.instance_id = instance_id
        self.instance_address = instance_address
        return self

    def get_instance_address(self) -> bytes:
        return self.instance_address

    def get_instance_id(self) -> int:
        return self.instance_id

    def get_max_storage(self) -> int:
        return self.max_storage

    def execute(self, caller: bytes, function_selector: int, function_param: bytes, execution_context: ExecutionContext):

        if function_selector == 1:  # create(token_a, amount_a, token_b, amount_b. fee_bps, assets_app_id)
            # TODO: this method is called on a governance event only
            offset = 0
            token_a = function_param[offset:offset+Assets.SYMBOL_LENGTH].decode(STR_ENCODING)
            offset += Assets.SYMBOL_LENGTH
            l = int.from_bytes(function_param[offset:offset+DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            token_a_amount = int.from_bytes(function_param[offset:offset+l], INT_ENCODING)
            offset += l
            token_b = function_param[offset:offset + Assets.SYMBOL_LENGTH].decode(STR_ENCODING)
            offset += Assets.SYMBOL_LENGTH
            l = int.from_bytes(function_param[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            token_b_amount = int.from_bytes(function_param[offset:offset + l], INT_ENCODING)
            offset += l
            fee_bps = int.from_bytes(function_param[offset:offset+2], INT_ENCODING)
            offset += 2
            if fee_bps > 10_000:
                raise Exception("Invalid fee amount")
            assets_app_id = int.from_bytes(function_param[offset:offset+APP_INSTANCE_ID_LENGTH], INT_ENCODING)

            # transfer seed token amount from caller to app
            assets_app = MAM.INSTANCE.id_to_app[assets_app_id]
            assets_app.execute(caller, 3, MAM.array_to_bytes([
                token_a.encode(STR_ENCODING) + MAM.pack_int(token_a_amount) + self.instance_address,
                token_b.encode(STR_ENCODING) + MAM.pack_int(token_b_amount) + self.instance_address,
            ]), execution_context)

            app_account_storage = execution_context.read_account_storage(self.instance_address)
            app_account_array = MAM.parse_array(app_account_storage, execution_context)
            app_account_assets_storage, app_account_assets_index = MAM.get_app_data_from_array(assets_app_id, app_account_array, execution_context)
            app_tokens = Assets.get_account_tokens(app_account_assets_storage, execution_context)
            if app_tokens[token_a][1] != Assets.TYPE_FUNGIBLE or app_tokens[token_b][1] != Assets.TYPE_FUNGIBLE:
                raise Exception("Invalid token type")
            if app_tokens[token_a][2] < token_a_amount or app_tokens[token_b][2] < token_b_amount:
                raise Exception("Should never happen")
            token_a_amount = app_tokens[token_a][2]
            token_b_amount = app_tokens[token_b][2]
            k = token_a_amount * token_b_amount

            # If the provider is minting a new pool, the number of liquidity tokens they will receive will equals sqrt(x * y)
            lp_amount = int(math.sqrt(k))

            # credit lp to caller
            caller_storage = execution_context.read_account_storage(caller)
            caller_array = MAM.parse_array(caller_storage, execution_context)
            caller_array.append(self.instance_id.to_bytes(APP_INSTANCE_ID_LENGTH, INT_ENCODING)
                                + MAM.INSTANCE.blockchain.bnum.to_bytes(BNUM_LENGTH, INT_ENCODING)
                                + MAM.pack_int(lp_amount)
                                )
            caller_storage = MAM.account_array_to_bytes(caller_array)
            execution_context.write_account_storage(caller_storage, caller_storage)

            app_storage = token_a.encode(STR_ENCODING) + int(app_tokens[token_a][1]).to_bytes(1, INT_ENCODING) \
                + token_b.encode(STR_ENCODING) + int(app_tokens[token_b][1]).to_bytes(1, INT_ENCODING) \
                + assets_app_id.to_bytes(APP_INSTANCE_ID_LENGTH, INT_ENCODING) \
                + MAM.pack_int(k) \
                + fee_bps.to_bytes(2, INT_ENCODING) \
                + MAM.pack_int(lp_amount) \
                + MAM.pack_int(0) \
                + MAM.pack_int(token_a_amount) \
                + MAM.pack_int(token_b_amount)
            execution_context.write_app_storage(self.instance_id, app_storage)
        elif function_selector == 2:  # set_fee(fee_bps)
            raise Exception("Not implemented")
        elif function_selector == 3:  # add_liquidity(amount_a, max_amount_b)
            offset = 0
            l = int.from_bytes(function_param[offset:offset+DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            token_a_amount = int.from_bytes(function_param[offset:offset + l], INT_ENCODING)
            offset += l
            l = int.from_bytes(function_param[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            token_b_max_amount = int.from_bytes(function_param[offset:offset + l], INT_ENCODING)
            offset += l

            app_storage = execution_context.read_app_storage(self.instance_id)
            offset = 0
            token_a = app_storage[offset:offset + Assets.SYMBOL_LENGTH]
            offset += Assets.SYMBOL_LENGTH
            token_a_type = app_storage[offset]
            offset += 1
            token_b = app_storage[offset:offset + Assets.SYMBOL_LENGTH]
            offset += Assets.SYMBOL_LENGTH
            token_b_type = app_storage[offset]

            caller_storage = execution_context.read_account_storage(caller)
            caller_array = MAM.parse_array(caller_storage, execution_context)
            caller_amm_storage, caller_amm_index = MAM.get_app_data_from_array(self.instance_id, caller_array, execution_context)
            if caller_amm_index >= 0:
                # withdraw first to reset bnum
                self.execute(caller, 4, bytes(0), execution_context)

            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            k = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l
            assets_app_id = int.from_bytes(app_storage[offset:offset + APP_INSTANCE_ID_LENGTH], INT_ENCODING)
            offset += APP_INSTANCE_ID_LENGTH
            fee_bps = int.from_bytes(app_storage[offset:offset + 2], INT_ENCODING)
            offset += 2

            app_storage_lp_offset = offset
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            total_lp = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            sum_bnum_i = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            token_a_reserve = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            token_b_reserve = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l

            app_account_storage = execution_context.read_account_storage(self.instance_id)
            app_account_array = MAM.parse_array(app_account_storage, execution_context)
            app_account_assets_storage, app_account_assets_index = MAM.get_app_data_from_array(assets_app_id, app_account_array, execution_context)
            app_tokens = Assets.get_account_tokens(app_account_assets_storage, execution_context)

            token_a_balance = app_tokens[token_a][2]
            token_b_balance = app_tokens[token_b][2]
            if token_a_balance < token_a_reserve:
                raise Exception("Bad debt token A")
            if token_b_balance < token_b_reserve:
                raise Exception("Bad debt token B")

            token_b_amount = int(token_a_amount * token_b_reserve * DECIMAL_SCALE / token_a_reserve / DECIMAL_SCALE)

            if token_b_amount > token_b_max_amount:
                raise Exception("Token B amount limit breached")

            # transfer token_a and token_b from caller to app
            assets_app = MAM.INSTANCE.id_to_app[assets_app_id]
            assets_app.execute(caller, 3, MAM.array_to_bytes([
                token_a.encode(STR_ENCODING) + MAM.pack_int(token_a_amount) + self.instance_address,
                token_b.encode(STR_ENCODING) + MAM.pack_int(token_b_amount) + self.instance_address,
            ]), execution_context)

            # https://github.com/Uniswap/v2-core/blob/master/contracts/UniswapV2Pair.sol#L110

            # updating LPs
            new_total_lp = int(total_lp * (token_a_reserve + token_a_amount) * DECIMAL_SCALE / token_a_reserve / DECIMAL_SCALE)
            caller_lp = new_total_lp - total_lp
            total_lp = new_total_lp
            sum_bnum_i += MAM.INSTANCE.blockchain.bnum
            token_a_reserve = token_a_reserve + token_a_amount
            token_b_reserve = token_b_reserve + token_b_amount

            # saving app storage
            app_storage = app_storage[:app_storage_lp_offset] + MAM.pack_int(total_lp) + MAM.pack_int(sum_bnum_i) \
                          + MAM.pack_int(token_a_reserve) + MAM.pack_int(token_b_reserve)
            execution_context.write_app_storage(self.instance_id, app_storage)

            # crediting lp_token to caller
            caller_storage = execution_context.read_account_storage(caller)
            caller_array = MAM.parse_array(caller_storage, execution_context)
            caller_amm_storage, caller_amm_index = MAM.get_app_data_from_array(self.instance_id, caller_array, execution_context)

            if caller_amm_index < 0:
                caller_array.append(self.instance_id.to_bytes(APP_INSTANCE_ID_LENGTH, INT_ENCODING) + MAM.INSTANCE.blockchain.bnum.to_bytes(BNUM_LENGTH, INT_ENCODING) + MAM.pack_int(caller_lp))
            else:
                raise Exception("LP already exists for caller")

            caller_storage = MAM.account_array_to_bytes(caller_array, execution_context)
            execution_context.write_account_storage(caller_storage, caller_storage)

            return 0
        elif function_selector == 4:  # withdraw_liquidity()

            app_storage = execution_context.read_app_storage(self.instance_id)
            offset = 0
            token_a = app_storage[offset:offset + Assets.SYMBOL_LENGTH]
            offset += Assets.SYMBOL_LENGTH
            token_a_type = app_storage[offset]
            offset += 1
            token_b = app_storage[offset:offset + Assets.SYMBOL_LENGTH]
            offset += Assets.SYMBOL_LENGTH
            token_b_type = app_storage[offset]
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            k = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l
            assets_app_id = int.from_bytes(app_storage[offset:offset + APP_INSTANCE_ID_LENGTH], INT_ENCODING)
            offset += APP_INSTANCE_ID_LENGTH
            fee_bps = int.from_bytes(app_storage[offset:offset + 2], INT_ENCODING)
            offset += 2
            app_storage_lp_offset = offset
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            total_lp = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            sum_bnum_i = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            token_a_reserve = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            token_b_reserve = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l

            app_account_storage = execution_context.read_account_storage(self.instance_id)
            app_account_array = MAM.parse_array(app_account_storage, execution_context)
            app_account_assets_storage, app_account_assets_index = MAM.get_app_data_from_array(assets_app_id, app_account_array, execution_context)
            app_tokens = Assets.get_account_tokens(app_account_assets_storage, execution_context)

            token_a_balance = app_tokens[token_a][2]
            token_b_balance = app_tokens[token_b][2]
            if token_a_balance < token_a_reserve:
                raise Exception("Bad debt token A")
            if token_b_balance < token_b_reserve:
                raise Exception("Bad debt token B")

            token_a_fee = token_a_balance - token_a_reserve
            token_b_fee = token_b_balance - token_b_reserve

            caller_storage = execution_context.read_account_storage(caller)
            caller_array = MAM.parse_array(caller_storage, execution_context)
            caller_amm_storage, caller_amm_index = MAM.get_app_data_from_array(self.instance_id, caller_array, execution_context)
            if caller_amm_index < 0:
                raise Exception("Caller has no LP")

            caller_bnum, caller_lp = AMM.parse_app_account_storage(caller_amm_storage, execution_context)

            # https://github.com/Uniswap/v2-core/blob/master/contracts/UniswapV2Pair.sol#L134
            caller_token_a_liquidity = int(token_a_reserve * caller_lp * DATA_LENGTH / total_lp / DECIMAL_SCALE)
            caller_token_b_liquidity = int(token_b_reserve * caller_lp * DATA_LENGTH / total_lp / DECIMAL_SCALE)

            # fee is proportional to LP share x time spent
            # TODO: only consider LP ?
            caller_token_a_fee = int(MAM.INSTANCE.blockchain.bnum - caller_bnum) * caller_lp * token_a_fee * DECIMAL_SCALE / sum_bnum_i / total_lp / DECIMAL_SCALE
            caller_token_b_fee = int(MAM.INSTANCE.blockchain.bnum - caller_bnum) * caller_lp * token_b_fee * DECIMAL_SCALE / sum_bnum_i / total_lp / DECIMAL_SCALE

            token_a_reserve -= caller_token_a_liquidity
            token_b_reserve -= caller_token_b_liquidity
            total_lp -= caller_lp
            sum_bnum_i -= caller_bnum

            if token_a_balance - caller_token_a_liquidity - caller_token_a_fee < token_a_reserve:
                raise Exception("Would be bad debt token A")
            if token_b_balance - caller_token_b_liquidity - caller_token_b_fee < token_b_reserve:
                raise Exception("Would be bad debt token B")

            # transfer liquidity + fee to caller
            caller_token_a_total = caller_token_a_liquidity + caller_token_a_fee
            caller_token_b_total = caller_token_b_liquidity + caller_token_b_fee
            assets_app = MAM.INSTANCE.id_to_app[assets_app_id]
            assets_app.execute(self.instance_address, 3, MAM.array_to_bytes([
                token_a.encode(STR_ENCODING) + MAM.pack_int(caller_token_a_total) + caller,
                token_b.encode(STR_ENCODING) + MAM.pack_int(caller_token_b_total) + caller,
            ]), execution_context)

            # delete AMM entry from caller storage
            caller_array.pop(caller_amm_index)
            caller_storage = MAM.account_array_to_bytes(caller_array, execution_context)
            execution_context.write_account_storage(caller_storage, caller_storage)

            # update app account storage
            app_account_assets_storage = Assets.update_balance(assets_app_id, app_account_assets_storage, token_a, token_a_type, -caller_token_a_total, execution_context)
            app_account_assets_storage = Assets.update_balance(assets_app_id, app_account_assets_storage, token_b, token_b_type, -caller_token_b_total, execution_context)
            app_account_array[app_account_assets_index] = app_account_assets_storage
            app_account_storage = MAM.account_array_to_bytes(app_account_array, execution_context)

            # update app storage
            app_storage = app_storage[:app_storage_lp_offset] \
                + MAM.pack_int(total_lp) + MAM.pack_int(sum_bnum_i) + MAM.pack_int(token_a_reserve) + MAM.pack_int(token_b_reserve)
            execution_context.write_app_storage(self.instance_id, app_storage)
        elif function_selector == 5:  # swap(a_to_b, amount_in, min_amount_out)
            a_to_b = function_param[0] > 0
            offset = 1
            l = int.from_bytes(function_param[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            amount_in = int.from_bytes(function_param[offset:offset + l], INT_ENCODING)
            offset += l
            l = int.from_bytes(function_param[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            min_amount_out = int.from_bytes(function_param[offset:offset + l], INT_ENCODING)

            app_storage = execution_context.read_app_storage(self.instance_id)
            offset = 0
            token_a = app_storage[offset:offset + Assets.SYMBOL_LENGTH].decode(STR_ENCODING)
            offset += Assets.SYMBOL_LENGTH
            token_a_type = app_storage[offset]
            offset += 1
            token_b = app_storage[offset:offset + Assets.SYMBOL_LENGTH].decode(STR_ENCODING)
            offset += Assets.SYMBOL_LENGTH
            token_b_type = app_storage[offset]
            offset += 1
            assets_app_id = int.from_bytes(app_storage[offset:offset + APP_INSTANCE_ID_LENGTH], INT_ENCODING)
            offset += APP_INSTANCE_ID_LENGTH
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            k = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l

            fee_bps = int.from_bytes(app_storage[offset:offset + 2], INT_ENCODING)
            offset += 2
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            total_lp = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            sum_bnum_i = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            token_a_reserve = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            token_b_reserve = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l

            app_account_storage = execution_context.read_account_storage(self.instance_address)
            app_account_array = MAM.parse_array(app_account_storage, execution_context)
            app_account_assets_storage, app_account_assets_index = MAM.get_app_data_from_array(assets_app_id, app_account_array, execution_context)
            app_tokens = Assets.get_account_tokens(app_account_assets_storage, execution_context)

            token_a_balance = app_tokens[token_a][2]
            token_b_balance = app_tokens[token_b][2]
            if token_a_balance < token_a_reserve:
                raise Exception("Bad debt token A")
            if token_b_balance < token_b_reserve:
                raise Exception("Bad debt token B")

            token_in = token_a
            token_in_reserve = token_a_reserve
            token_out = token_b
            token_out_reserve = token_b_reserve
            if not a_to_b:
                token_in = token_b
                token_in_reserve = token_b_reserve
                token_out = token_a
                token_out_reserve = token_a_reserve
            net_amount_in = int(amount_in - amount_in * fee_bps * DECIMAL_SCALE / 10000 / DECIMAL_SCALE)
            amount_out = int(token_out_reserve - k / (token_in_reserve + net_amount_in))
            if amount_out < min_amount_out:
                raise Exception("Not enough output")

            assets_app = MAM.INSTANCE.id_to_app[assets_app_id]
            # transfer token in from caller to app
            assets_app.execute(caller, 3, MAM.array_to_bytes([
                token_in.encode(STR_ENCODING) + MAM.pack_int(amount_in) + self.instance_address,
            ]), execution_context)
            # transfer token out from app to caller
            assets_app.execute(self.instance_address, 3, MAM.array_to_bytes([
                token_out.encode(STR_ENCODING) + MAM.pack_int(amount_out) + caller,
            ]), execution_context)

            #TODO: readjust k for rounding error ?

            return 0
        else:
            raise Exception("No such method")

    @staticmethod
    def parse_app_account_storage(storage, execution_context: ExecutionContext = ExecutionContext.no_op()):
        execution_context.op(4)
        offset = APP_INSTANCE_ID_LENGTH
        bnum = int.from_bytes(storage[offset:offset + BNUM_LENGTH], INT_ENCODING)
        offset += BNUM_LENGTH
        execution_context.op(6)
        l = int.from_bytes(storage[offset:offset + DATA_LENGTH], INT_ENCODING)
        offset += DATA_LENGTH
        execution_context.op(8)
        lp = int.from_bytes(storage[offset:offset + l], INT_ENCODING)
        return bnum, lp


class MarketPlace(ApplicationInstance):

    def __init__(self):
        self.instance_address = None
        self.instance_id = None
        self.max_storage = 1024

    def init(self, instance_id: int, instance_address: bytes) -> 'ApplicationInstance':
        self.instance_id = instance_id
        self.instance_address = instance_address
        return self

    def get_instance_address(self) -> bytes:
        return self.instance_address

    def get_instance_id(self) -> int:
        return self.instance_id

    def get_max_storage(self) -> int:
        return self.max_storage

    def execute(self, caller: bytes, function_selector: int, function_param: bytes, execution_context: ExecutionContext):
        if function_selector == 1:  # create(offer_fee_mcm, match_fee_mcm, assets_app_id)
            offset = 0
            l = int.from_bytes(function_param[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            offer_fee_mcm = int.from_bytes(function_param[offset:offset + l], INT_ENCODING)
            offset += l
            l = int.from_bytes(function_param[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            match_fee_mcm = int.from_bytes(function_param[offset:offset + l], INT_ENCODING)
            offset += l
            assets_app_id = int.from_bytes(function_param[offset:offset + APP_INSTANCE_ID_LENGTH], INT_ENCODING)

            app_storage = MAM.pack_int(offer_fee_mcm) + MAM.pack_int(match_fee_mcm) + assets_app_id.to_bytes(APP_INSTANCE_ID_LENGTH, INT_ENCODING) + MAM.pack_int(0)
            execution_context.write_app_storage(self.instance_id, app_storage)

            return 0
        elif function_selector == 2:  # list(my_goods=[(symbol, value)], my_price=[(symbol, value)], counterparty)
            offset = 0
            l = int.from_bytes(function_param[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            caller_goods = MAM.parse_array(function_param[offset:offset+l])
            offset += l
            l = int.from_bytes(function_param[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            caller_price = MAM.parse_array(function_param[offset:offset + l])
            offset += l
            counterparty = function_param[offset:offset+12]

            offset = 0
            app_storage = execution_context.read_app_storage(self.instance_id)
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            offer_fee_mcm = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            match_fee_mcm = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l
            assets_app_id = int.from_bytes(app_storage[offset:offset + APP_INSTANCE_ID_LENGTH], INT_ENCODING)
            offset += APP_INSTANCE_ID_LENGTH
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            total = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)

            #TODO: transfer fee to stacker and treasury

            # Transfer offset asset to app account
            transfer_payload = []
            for e in caller_goods:
                transfer_payload.append(e+self.instance_address)
            assets = MAM.INSTANCE.id_to_app[assets_app_id]
            assets.execute(caller, 3, MAM.array_to_bytes(transfer_payload), execution_context)

            caller_goods_storage = MAM.array_to_bytes(caller_goods, execution_context)
            caller_price_storage = MAM.array_to_bytes(caller_price, execution_context)
            caller_payload = MAM.array_to_bytes([
                MAM.pack_int(total) + len(caller_goods_storage).to_bytes(DATA_LENGTH, INT_ENCODING) + caller_goods_storage
                + len(caller_price_storage).to_bytes(DATA_LENGTH, INT_ENCODING) + caller_price_storage
            ])

            caller_storage = execution_context.read_account_storage(caller)
            caller_array = MAM.parse_array(caller_storage, execution_context)
            caller_mp_storage, caller_mp_index = MAM.get_app_data_from_array(self.instance_id, caller_array, execution_context)

            if caller_mp_index < 0:
                caller_array.append(self.instance_id.to_bytes(APP_INSTANCE_ID_LENGTH, INT_ENCODING)+caller_payload)
            else:
                caller_mp_array = MAM.parse_array(caller_mp_storage, execution_context)
                caller_mp_array.append(caller_payload)
                caller_array[caller_mp_index] = self.instance_id.to_bytes(APP_INSTANCE_ID_LENGTH, INT_ENCODING) + MAM.array_to_bytes(caller_mp_array, execution_context)

            caller_storage = MAM.account_array_to_bytes(caller_array, execution_context)
            execution_context.write_account_storage(caller, caller_storage)

            return 0
        elif function_selector == 3: # match(user_address, listing_id)
            offset = 0
            seller_address = function_param[offset:offset+12]
            offset += 12
            l = int.from_bytes(function_param[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            offer_id = int.from_bytes(function_param[offset:offset + l], INT_ENCODING)

            offset = 0
            app_storage = execution_context.read_app_storage(self.instance_id)
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            offer_fee_mcm = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            match_fee_mcm = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)
            offset += l
            assets_app_id = int.from_bytes(app_storage[offset:offset + APP_INSTANCE_ID_LENGTH], INT_ENCODING)
            offset += APP_INSTANCE_ID_LENGTH
            l = int.from_bytes(app_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            total = int.from_bytes(app_storage[offset:offset + l], INT_ENCODING)

            seller_storage = execution_context.read_account_storage(seller_address)
            seller_array = MAM.parse_array(seller_storage, execution_context)
            seller_mp_storage, seller_mp_index = MAM.get_app_data_from_array(self.instance_id, seller_array, execution_context)
            if seller_mp_index < 0:
                raise Exception("Offer id not found")

            offer_goods = None
            offer_price = None
            offer_counterparty = None

            for e in MAM.parse_array(seller_mp_storage[APP_INSTANCE_ID_LENGTH:], execution_context):
                offset = 0
                l = int.from_bytes(e[offset:offset + DATA_LENGTH], INT_ENCODING)
                offset += DATA_LENGTH
                _id = int.from_bytes(e[offset:offset+l], INT_ENCODING)
                if _id == offer_id:
                    offset += l
                    l = int.from_bytes(e[offset:offset + DATA_LENGTH], INT_ENCODING)
                    offset += DATA_LENGTH
                    offer_goods = MAM.parse_array(e[offset:offset+l])
                    offset += l

                    l = int.from_bytes(e[offset:offset + DATA_LENGTH], INT_ENCODING)
                    offset += DATA_LENGTH
                    offer_price = MAM.parse_array(e[offset:offset+l])
                    offset += l
                    offer_counterparty = e[offset:offset+12]

                if offer_goods is None:
                    raise Exception("Offer not found")
                if offer_counterparty == bytes(12) and offer_counterparty != caller:
                    raise Exception("Private sale")

                assets = MAM.INSTANCE.id_to_app[assets_app_id]

                # Transfer price asset from caller to offer user
                transfer_price = []
                for e in offer_price:
                    transfer_price.append(e+seller_address)

                assets.execute(caller, 3, MAM.array_to_bytes(transfer_price), execution_context)

                # Transfer offer asset from app account to caller
                transfer_offer = []
                for e in offer_goods:
                    transfer_offer.append(e + caller)

                assets.execute(self.instance_address, 3, MAM.array_to_bytes(transfer_offer), execution_context)

                return 0
        elif function_selector == 4: # cancel(offer_id)
            raise Exception("Not implemented")
        else:
            raise Exception("No such method")


class Chat(ApplicationInstance):

    def __init__(self):
        self.instance_address = None
        self.instance_id = None
        self.max_storage = 1024

    def init(self, instance_id: int, instance_address: bytes) -> 'ApplicationInstance':
        self.instance_id = instance_id
        self.instance_address = instance_address
        return self

    def get_instance_address(self) -> bytes:
        return self.instance_address

    def get_instance_id(self) -> int:
        return self.instance_id

    def get_max_storage(self) -> int:
        return self.max_storage

    def execute(self, caller: bytes, function_selector: int, function_param: bytes, execution_context: ExecutionContext):

        if function_selector == 1:  # send(recipient, msg)
            offset = 0
            l = int.from_bytes(function_param[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            recipient = function_param[offset:offset + l]
            offset += l
            l = int.from_bytes(function_param[offset:offset + DATA_LENGTH], INT_ENCODING)
            offset += DATA_LENGTH
            msg = function_param[offset:offset + l]
            offset += l

            caller_storage = execution_context.read_account_storage(caller)
            caller_array = MAM.parse_array(caller_storage, execution_context)
            caller_app_storage, caller_app_index = MAM.get_app_data_from_array(self.instance_id, caller_array, execution_context)

            caller_app_storage = self.instance_id.to_bytes(APP_INSTANCE_ID_LENGTH, INT_ENCODING) + function_param
            MAM.set_to_array(caller_app_storage, caller_array, caller_app_index, execution_context)
            caller_storage = MAM.account_array_to_bytes(caller_array, execution_context)
            execution_context.write_account_storage(caller, caller_storage)

            return 0
        else:
            raise Exception("No such method")

    @staticmethod
    def decode_entry( entry_storage: bytes) -> str:
        offset = 0
        l = int.from_bytes(entry_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
        offset += DATA_LENGTH
        recipient = entry_storage[offset:offset + l]
        offset += l
        l = int.from_bytes(entry_storage[offset:offset + DATA_LENGTH], INT_ENCODING)
        offset += DATA_LENGTH
        msg = entry_storage[offset:offset + l]
        return '@{}:{}'.format(recipient.decode(STR_ENCODING), msg.decode(STR_ENCODING))


class MAM:

    INSTANCE: Union['MAM', None] = None

    def __init__(self):
        self.app_templates: List[ApplicationTemplate] = []
        self.address_to_app: Dict[bytes, ApplicationInstance] = {}
        self.id_to_app: Dict[int, ApplicationInstance] = {}
        self.app_storage = Storage()
        self.account_storage = Storage()

        self.add_app_template(ApplicationTemplate(APP_TEMPLATE_TYPE_MCM))
        self.id_to_app[MCM_APP_ID] = MCM()

        self.next_instance_id = 1
        self.blockchain = Blockchain()

        if MAM.INSTANCE is not None:
            raise Exception("Multiple MAM instance are not allowed")
        MAM.INSTANCE = self

    def add_app_template(self, app_template: ApplicationTemplate):
        for at in self.app_templates:
            if at.type == app_template.type:
                raise Exception("Application Template type {} already exists".format(app_template.type))
        self.app_templates.append(app_template)

    @staticmethod
    def new_app(app_template: 'ApplicationTemplate') -> ApplicationInstance:
        if app_template.type == APP_TEMPLATE_TYPE_ASSETS:
            return Assets()
        elif app_template.type == APP_TEMPLATE_TYPE_AMM:
            return AMM()
        elif app_template.type == APP_TEMPLATE_TYPE_MARKETPLACE:
            return MarketPlace()
        elif app_template.type == APP_TEMPLATE_TYPE_CHAT:
            return Chat()
        else:
            raise Exception("Unknown Application Template type {}".format(app_template.type))

    def create_instance(self, app_template_type: int):
        app_template = None
        for at in self.app_templates:
            if at.type == app_template_type:
                app_template = at
                break
        if app_template is None:
            raise Exception("Unknown Application Template type {}".format(app_template_type))

        app_instance = MAM.new_app(app_template).init(self.next_instance_id, bytes.fromhex("00000000000000000000") + self.next_instance_id.to_bytes(2, INT_ENCODING))
        self.next_instance_id += 1
        self.account_storage.write(app_instance.get_instance_address(), bytes(0))
        self.id_to_app[app_instance.get_instance_id()] = app_instance
        self.address_to_app[app_instance.get_instance_address()] = app_instance

        return app_instance.get_instance_id()

    def call(self, dry_run: bool, caller_address: bytes, max_gas: Union[int, None], app_id: int, function_selector: int, function_parameters:  bytes):
        """

        :param dry_run: to estimate the gas cost of a transaction without persisting change on chain. This is equivalent to EVM 'estimate_gas' function
        :param caller_address:
        :param max_gas:
        :param app_id:
        :param function_selector:
        :param function_parameters:
        :return:
        """
        if app_id not in self.id_to_app:
            raise Exception("Application id {} not found".format(app_id))
        if not dry_run and max_gas is None:
            raise Exception("Must specify max_gas when not dry run")
        app = self.id_to_app[app_id]
        exec_ctx = ExecutionContext(max_gas, self.app_storage, self.account_storage)

        try:
            caller_storage = self.account_storage.read(caller_address)
            caller_array = MAM.parse_array(caller_storage)
            caller_mcm_app_storage, caller_mcm_app_index = MAM.get_app_data_from_array(MCM_APP_ID, caller_array)
            balance = MCM.get_balance(caller_mcm_app_storage)
            if not dry_run and balance < max_gas * GAS_PRICE:
                raise Exception("Not enough balance for gas (max gas cost = {})".format(max_gas * GAS_PRICE))  # a wetrun without balance should not even make it to the MAM
            if max_gas is not None:
                # substract max_gas cost from caller balance before executing to insure gas cost is funded
                caller_mcm_app_storage = MCM.subtract_from_balance(caller_mcm_app_storage, max_gas * GAS_PRICE)
                caller_array[caller_mcm_app_index] = caller_mcm_app_storage
                caller_storage = MAM.account_array_to_bytes(caller_array)
                exec_ctx.write_account_storage(caller_address, caller_storage, update_gas=False)
            try:
                app.execute(caller_address, function_selector, function_parameters, exec_ctx)
            finally:
                if max_gas is not None:
                    # credit max_gas cost back
                    caller_storage = exec_ctx.read_account_storage(caller_address, update_gas=False)
                    caller_array = MAM.parse_array(caller_storage)
                    caller_mcm_app_storage, caller_mcm_app_index = MAM.get_app_data_from_array(MCM_APP_ID, caller_array)
                    caller_mcm_app_storage = MCM.add_to_balance(caller_mcm_app_storage, max_gas * GAS_PRICE)
                    caller_array[caller_mcm_app_index] = caller_mcm_app_storage
                    caller_storage = MAM.array_to_bytes(caller_array)
                    exec_ctx.write_account_storage(caller_address, caller_storage, update_gas=False)

            if len(self.app_storage.read(app_id)) > app.get_max_storage():
                raise Exception("App storage overflow")


        except:
            # In case of error, the miner collect all the gas available
            if max_gas is not None: # not a dry run
                exec_ctx.total_gas = max_gas
            exec_ctx.error = traceback.format_exc()

        gas_used = exec_ctx.total_gas
        gas_cost = gas_used * GAS_PRICE

        if not dry_run:
            caller_storage = exec_ctx.read_account_storage(caller_address, update_gas=False)
            caller_array = MAM.parse_array(caller_storage)
            caller_mcm_app_storage, caller_mcm_app_index = MAM.get_app_data_from_array(MCM_APP_ID, caller_array)
            balance = MCM.get_balance(caller_mcm_app_storage)
            caller_mcm_app_storage = MCM.set_balance(caller_mcm_app_storage, max(0, balance - gas_cost))
            caller_array[caller_mcm_app_index] = caller_mcm_app_storage
            caller_storage = MAM.array_to_bytes(caller_array)
            exec_ctx.write_account_storage(caller_address, caller_storage, update_gas=False)
            # flush storage buffer
            exec_ctx.persists()

        # recompute the hash of account storage that have been charged
        for addr, data in exec_ctx.account_storage_buffer.items():
            pass #TODO: compute storage hash of each changed account

        return gas_used, gas_cost, exec_ctx.error

    @staticmethod
    def parse_array(array_storage: bytes, execution_context: ExecutionContext = ExecutionContext.no_op()):
        execution_context.op(3)
        if len(array_storage) <= 0:
            return []
        execution_context.op(1)
        entries = []
        execution_context.op(2)
        size = array_storage[0]  # max 255
        execution_context.op(2)
        offset = 1
        for i in range(size):
            execution_context.op(1)
            execution_context.op(5)
            l = int.from_bytes(array_storage[offset:offset+DATA_LENGTH], INT_ENCODING)
            execution_context.op(6)
            entries.append(array_storage[offset+DATA_LENGTH:offset+DATA_LENGTH+l])
            execution_context.op(3)
            offset += DATA_LENGTH + l
        return entries

    @staticmethod
    def array_to_bytes(array: list, execution_context: ExecutionContext = ExecutionContext.no_op()) -> bytes:
        execution_context.op(2)
        if len(array) > 255:
            raise Exception("Array is too large")
        buffer = len(array).to_bytes(1, INT_ENCODING)
        for e in array:
            if len(e) > 0:
                buffer += len(e).to_bytes(DATA_LENGTH, INT_ENCODING) + e
        return bytes(buffer)

    @staticmethod
    def set_to_array(value: bytes, array: list, index: int, execution_context: ExecutionContext = ExecutionContext.no_op()):
        execution_context.op(2)
        if index < 0:
            execution_context.op(1)
            array.append(value)
        else:
            execution_context.op(1)
            array[index] = value

    @staticmethod
    def account_array_to_bytes(account_array: list, execution_context: ExecutionContext = ExecutionContext.no_op()):
        sorted_account_arrays = list(account_array)
        sorted_account_arrays.sort(key=lambda app_storage: int.from_bytes(app_storage[:APP_INSTANCE_ID_LENGTH], INT_ENCODING))
        return MAM.array_to_bytes(sorted_account_arrays, execution_context)

    @staticmethod
    def get_app_data_from_array(app_instance_id: int, account_array: list, execution_context: ExecutionContext = ExecutionContext.no_op()) -> (bytes, int):
        for i in range(len(account_array)):
            execution_context.op(1)
            execution_context.op(1)
            app_storage = account_array[i]
            execution_context.op(1)
            execution_context.op(1)
            if int.from_bytes(app_storage[:APP_INSTANCE_ID_LENGTH], INT_ENCODING) == app_instance_id:
                return app_storage, i
        return bytes(0), -1

    @staticmethod
    def int_byte_size(value: int):
        b = (value.bit_length() + 7) // 8
        if b > (1 << (11 << DATA_LENGTH)) - 1:
            raise Exception("Overflow")
        return b

    @staticmethod
    def pack_int(value: int) -> bytes:
        assert type(value) == int
        l = MAM.int_byte_size(value)
        return l.to_bytes(DATA_LENGTH, INT_ENCODING) + value.to_bytes(l, INT_ENCODING)


