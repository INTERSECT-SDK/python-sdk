import threading


class MultiFlagThreadEvent:
    """Only set a single threading event if all flags are set.

    NOTE: This is an internal API and does not do validation or control flow
    with arguments to its methods.
    """

    def __init__(self, num_flags: int) -> None:
        """Constructor.

        Params:
          num_flags: This should be a positive value.
            You may suffer performance issues if this is >= 63
        """
        self._flag = threading.Event()
        self._bitmask = 0b0
        """Value which gets modified. If it equals bitmask_target, set the flag; otherwise, don't."""
        self._bitmask_target = (1 << num_flags) - 1
        """Immutable number where all bits are set to 1"""

    def unset_all(self) -> None:
        """Clear all flags."""
        self._flag.clear()
        self._bitmask = 0b0

    def set_all(self) -> None:
        """Set all flags."""
        self._flag.set()
        self._bitmask = self._bitmask_target

    def set_nth_flag(self, flag: int) -> None:
        """Set a flag.

        If all other flags are set, this sets the threading event.

        Params:
          flag: position of flag you want to set (0-indexed), should be less than the value provided in the constructor
        """
        self._bitmask |= 1 << flag
        if self._bitmask == self._bitmask_target:
            self._flag.set()

    def unset_nth_flag(self, flag: int) -> None:
        """Unset a flag and the threading event.

        Params:
          flag: position of flag you want to set (0-indexed), should be less than the value provided in the constructor
        """
        self._bitmask &= ~(1 << flag)
        self._flag.clear()

    def is_nth_flag_set(self, flag: int) -> bool:
        """Check to see if a specific flag is set.

        Params:
          flag: position of flag you want to check (0-indexed), should be less than the value provided in the constructor
        """
        return (self._bitmask >> flag) & 1 == 1

    def wait(self, amount: float) -> None:
        """Block until internal flag is True, which will only happen once all other flags are set.

        Params:
          amount: time to block
        """
        self._flag.wait(amount)

    def is_set(self) -> bool:
        """Determine if flag was set. Useful as the "while" condition for application loops.

        Returns:
          True if set, False otherwise
        """
        return self._flag.is_set()
