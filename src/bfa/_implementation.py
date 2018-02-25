import sys

import attr


if sys.version_info.major == 2:
    from collections import Mapping

    class MappingProxyType(Mapping):
        """
        Read-only proxy of a mapping.  It provides a dynamic view on
        the mapping’s entries, which means that when the mapping
        changes, the view reflects these changes.
        """
        __slots__ = ("_mapping",)

        def __init__(self, mapping):
            self._mapping = mapping

        def __getitem__(self, item):
            """
            Return the item of the underlying mapping with key key.
            Raises a KeyError if key is not in the underlying mapping.
            """
            return self._mapping[item]

        def __iter__(self):
            """
            Return an iterator over the keys of the underlying
            mapping.  This is a shortcut for iter(proxy.keys()).
            """
            return iter(self._mapping)

        def __len__(self):
            """
            Return the number of items in the underlying mapping.
            """
            return len(self._mapping)

        def copy(self):
            """
            """
            return self._mapping.copy()

        def __repr__(self):
            return "mappingproxy({!r})".format(self._mapping)

else:
    from types import MappingProxyType


class ConsumedArgument(Exception):
    """
    Raised when an argument has already been added to the builder.

    :ivar cls: The :py:mod:`attr` decorated class being built.
    :ivar consumed: The name of the consumed argument

    :type consumed: :py:class:`str`
    """

    def __init__(self, cls, consumed):
        self.cls = cls
        self.consumed = consumed
        super(Exception, self).__init__(
            "Attempted to set value for consumed attribute"
            " {consumed!r} of class {cls}".format(
                cls=self.cls, consumed=self.consumed,
            )
        )


class IncompleteArguments(Exception):
    """
    Raised when :py:meth:`_Builds.build` is called but not all required
    arguments have been provided.

    :ivar cls: The :py:mod:`attr` decorated class being built.
    :ivar present: The provided arguments.
    :type present: :py:class:`frozenset`

    :ivar missing: The missing arguments.
    :type missing: :py:class:`frozenset`
    """
    def __init__(self, cls, present, missing):
        self.cls = cls
        self.present = present
        self.missing = missing
        super(Exception, self).__init__(
            "Attempted construction of incomplete class"
            " {cls}: have {present}, need {missing}".format(
                cls=cls, present=self.present, missing=self.missing,
            )
        )


@attr.s(frozen=True)
class _Building(object):
    """
    An in-progress builder.  This is an intermediary that collects
    argument values.

    Don't use this directly!  Instead, call :py:func:`build`.
    """
    _cls = attr.ib()
    _arguments = attr.ib(MappingProxyType({}))

    _all_arguments = attr.ib()
    _required_arguments = attr.ib()
    _consumed_arguments = attr.ib(frozenset())

    @_all_arguments.default
    def determine_names(self):
        """
        Determine all argument names for the wrapped class.
        """
        return frozenset(a.name for a in attr.fields(self._cls))

    @_required_arguments.default
    def create_required(self):
        """
        Determine all required names for the wrapped class.
        """
        return frozenset(
            a.name
            for a in attr.fields(self._cls)
            if a.default is attr.NOTHING
        )

    def __getattr__(self, name):
        if name in self._all_arguments:
            new_arguments = dict(self._arguments)

            def set_value(value):
                new_arguments[name] = value
                return attr.evolve(
                    self,
                    arguments=MappingProxyType(new_arguments),
                    all_arguments=self._all_arguments - {name},
                    required_arguments=self._required_arguments - {name},
                    consumed_arguments=self._consumed_arguments | {name},
                )

            set_value.__name__ = name
            set_value.__doc__ = (
                "Set the argument {!r} for a new instance of {!r}".format(
                    name, self._cls,
                )
            )

            return set_value
        elif name in self._consumed_arguments:
            raise ConsumedArgument(self._cls, name)
        else:
            raise AttributeError(name)

    def build(self):
        """
        Build an instance of the wrapped class with the provided
        arguments.

        :raises: :py:exc:`IncompleteArguments` if required arguments
                 remain unspecified.
        """

        if self._required_arguments:
            raise IncompleteArguments(
                self._cls,
                present=frozenset(self._arguments),
                missing=frozenset(self._required_arguments),
            )
        return self._cls(**self._arguments)


def builder(for_class):
    """
    Construct a builder for an :py:mod:`attr` decorated class.

    Add arguments by calling methods with their names:

    >>> import attr
    >>> from bfa import builder
    >>> Class = attr.make_class("Class", ["a", "b"])
    >>> class_builder = builder(for_class=Class)
    >>> with_a = class_builder.a(1)

    Adding an argument creates a new immutable builder:

    >>> with_b = with_a.b(2)
    >>> with_a is with_b
    False

    Arguments can't be added twice:

    >>> with_a.a(1)  # doctest: +NORMALIZE_WHITESPACE
    Traceback (most recent call last):
    ConsumedArgument: Attempted to set value for
                      consumed attribute 'a' of
                      class <class '_implementation.Class'>

    Unknown arguments aren't allowed:

    >>> with_a.unknown("value")
    Traceback (most recent call last):
    AttributeError: unknown

    Create an instance by calling :py:meth:`build`:

    >>> with_b.build()
    Class(a=1, b=2)

    But instances can't be created without all their required
    arguments:

    >>> with_a.build()  # doctest: +NORMALIZE_WHITESPACE
    Traceback (most recent call last):
    IncompleteArguments: Attempted construction of incomplete class
                         <class '_implementation.Class'>:
                         have frozenset(['a']), need frozenset(['b'])
    """
    return _Building(for_class)
