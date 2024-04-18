from intersect_sdk import intersect_message


class ReturnTypeMismatch:
    @intersect_message()
    def wrong_return_annotation(self, param: int) -> int:
        return 'red'
