from poc_implementation.mip12.storage import Storage


class ExecutionContext:
    GAS_SIMPLE_OP = 1
    GAS_READ_STORAGE = GAS_SIMPLE_OP * 10
    GAS_WRITE_STORAGE_BASE = GAS_READ_STORAGE * 10
    GAS_WRITE_STORAGE_PER_BYTE = 10

    def __init__(self, max_gas: int, app_storage: Storage, account_storage: Storage, no_op: bool = False):
        self.max_gas = max_gas
        self.app_storage = app_storage
        self.app_storage_buffer = {}
        self.account_storage = account_storage
        self.account_storage_buffer = {}
        self.total_gas = 0
        self.error = None
        self.no_op = no_op

    def _check_gas(self):
        if self.no_op:
            return
        if self.max_gas is not None and self.total_gas > self.max_gas:
            raise Exception("Out of gas")

    def op(self, multi=1):
        if self.no_op:
            return
        self.total_gas += ExecutionContext.GAS_SIMPLE_OP * multi
        self._check_gas()

    def read_app_storage(self, key):
        self.total_gas += ExecutionContext.GAS_READ_STORAGE
        self._check_gas()
        if key not in self.app_storage_buffer:
            if key not in self.app_storage.db:
                return bytes(0)
            else:
                return self.app_storage.read(key)
        else:
            return self.app_storage_buffer[key]

    def write_app_storage(self, key, value):
        self.total_gas += ExecutionContext.GAS_WRITE_STORAGE_BASE + ExecutionContext.GAS_WRITE_STORAGE_PER_BYTE * len(value)
        self._check_gas()
        self.app_storage_buffer[key] = value

    def read_account_storage(self, key, update_gas=True):
        if update_gas:
            self.total_gas += ExecutionContext.GAS_READ_STORAGE
            self._check_gas()
        if key not in self.account_storage_buffer:
            if key not in self.account_storage.db:
                return bytes(0)
            else:
                return self.account_storage.read(key)
        else:
            return self.account_storage_buffer[key]

    def write_account_storage(self, key, value, update_gas=True):
        if update_gas:
            self.total_gas += ExecutionContext.GAS_WRITE_STORAGE_BASE + ExecutionContext.GAS_WRITE_STORAGE_PER_BYTE * len(value)
            self._check_gas()
        self.account_storage_buffer[key] = value

    def total_gas_used(self):
        if self.no_op:
            raise Exception("NO-OP")
        return self.total_gas

    def persists(self):
        for key in self.app_storage_buffer:
            self.app_storage.write(key, self.app_storage_buffer[key])
        for key in self.account_storage_buffer:
            self.account_storage.write(key, self.account_storage_buffer[key])

    @staticmethod
    def no_op():
        return ExecutionContext(-1, None, None, True)

