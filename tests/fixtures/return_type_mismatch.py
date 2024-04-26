from intersect_sdk import IntersectBaseCapabilityImplementation, intersect_message


class ReturnTypeMismatch(IntersectBaseCapabilityImplementation):
    @intersect_message()
    def wrong_return_annotation(self, param: int) -> int:
        return 'red'
