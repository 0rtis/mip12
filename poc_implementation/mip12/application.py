from poc_implementation.mip12.execution_context import ExecutionContext


class ApplicationInstance:
    def execute(self, caller: bytes, function_selector: int, function_param: bytes, execution_context: ExecutionContext):
        pass

    def init(self, instance_id: int, instance_address: bytes) -> 'ApplicationInstance':
        pass

    def get_instance_id(self) -> int:
        pass

    def get_instance_address(self) -> bytes:
        pass

    def get_max_storage(self) -> int:
        pass


class ApplicationTemplate:
    def __init__(self, _type: int):
        self.type = _type


