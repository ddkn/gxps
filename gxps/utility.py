"""Provides utility classes for Observer pattern and Singleton pattern."""
# pylint: disable=logging-format-interpolation

import logging
import uuid


LOG = logging.getLogger(__name__)


class Borg(object):
    """Alternative to Singleton pattern: all instances have the same state."""
    # pylint: disable=too-few-public-methods
    __shared_state = {}
    def __init__(self, *args, shared_state=None, **kwargs):
        # pylint: disable=access-member-before-definition
        super().__init__(*args, **kwargs)
        if shared_state is None:
            shared_state = self.__shared_state
        if not shared_state:
            shared_state.update(self.__dict__)
        self.__dict__ = shared_state

    @classmethod
    def cleanup(cls):
        """Cleans up the object. Mainly for testing."""
        cls.__shared_state.clear()


class Event:        # pylint: disable=too-few-public-methods
    """Stores variables during emitting."""
    def __init__(self, **kwargs):
        self.signal = "generic"
        for attr, value in kwargs.items():
            setattr(self, attr, value)

    def __getattr__(self, attr):
        try:
            return super().__getattr__(attr)
        except AttributeError:
            return None


class Observable:
    """Provides methods for observing these objects via callbacks.
    """
    _signals = (
        "changed",
        "changed-spectra",
        "changed-spectrum",
        "changed-metadata",
        "changed-fit",
        "changed-peak"
    )
    def __init__(self, *args, **kwargs):
        self._observers = dict((signal, {}) for signal in self._signals)
        self._propagators = {}
        super().__init__(*args, **kwargs)

    @property
    def signals(self):
        """Makes signals accessible."""
        return self._signals

    def connect(self, signal, cb_func, *args, **kwargs):
        """Registers cb_func as a callback for the specified signal. signal
        has to be in self._signals.
        """
        handler_id = uuid.uuid1()
        if signal not in self._observers:
            raise ValueError("Unknown signal '{}'".format(signal))
        self._observers[signal][handler_id] = (cb_func, args, kwargs)
        return handler_id

    def disconnect(self, handler_id):
        """Deregisters cb_func as a callback for the specified signal.
        """
        for signal in self._observers:
            self._observers[signal].pop(handler_id, None)

    def disconnect_all(self):
        """Deregisters all cb_funcs.
        """
        for signal in self._observers:
            self._observers[signal].clear()

    def _start_propagating(self, child, signal):
        """Emit the same signal as child."""
        handler_id = child.connect(signal, self._re_emit)
        self._propagators[handler_id] = child
        return handler_id

    def _re_emit(self, event):
        kwargs = vars(event)
        kwargs["re_emitted"] = True
        signal = kwargs.pop("signal", None)
        self._emit(signal, **kwargs)

    def _stop_propagating(self, handler_id):
        """Stop re-emitting the signal from child."""
        child = self._propagators.pop(handler_id)
        child.disconnect(handler_id)

    def _stop_propagating_all(self, child):
        """Stop re-emitting all signals from child."""
        handler_ids = []
        for handler_id in self._propagators:
            if self._propagators[handler_id] == child:
                handler_ids.append(handler_id)
        for handler_id in handler_ids:
            self._stop_propagating(handler_id)

    def _emit(self, signal, **attrs):
        """Calls callbacks for signal signal."""
        # pylint: disable=attribute-defined-outside-init
        event = Event()
        event.source = attrs.pop("source", self)
        event.signal = attrs.pop("signal", signal)
        for key, value in attrs.items():
            setattr(event, key, value)
        for handler_id in self._observers[signal]:
            cb_func, args, kwargs = self._observers[signal][handler_id]
            cb_func(event, *args, **kwargs)
