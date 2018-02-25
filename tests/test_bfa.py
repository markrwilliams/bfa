import keyword
import string
import sys

import attr
import operator
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from hypothesis.stateful import Bundle, RuleBasedStateMachine, rule

from bfa import ConsumedArgument, IncompleteArguments, builder


@pytest.mark.skipif(sys.version_info.major > 2,
                    reason="MappingProxyType comes with >= Python 3.3")
class TestMappingProxyType(object):
    """
    Tests for :py:class:`MappingProxyType`.
    """

    @given(dictionary=st.dictionaries(st.text(), st.text()))
    def test_dict_equivalency(self, dictionary):
        """
        :py:class:`MappingProxyType`s match the read interface of
        :py:class:`dict`s.
        """
        from bfa._implementation import MappingProxyType

        mappingproxy = MappingProxyType(dictionary)

        # iter
        assert list(mappingproxy) == list(dictionary)

        assert mappingproxy.keys() == dictionary.keys()
        assert mappingproxy.values() == dictionary.values()
        assert mappingproxy.items() == dictionary.items()

        for k in dictionary:
            # getitem
            assert mappingproxy[k] == dictionary[k]
            assert mappingproxy.get(k) == dictionary.get(k)
            # contains
            assert k in mappingproxy

        assert len(mappingproxy) == len(dictionary)

        # negative test cases
        assert 0 not in dictionary and 0 not in mappingproxy

        default = 'value'
        assert dictionary.get(0) is mappingproxy.get(0)
        assert dictionary.get(0, default) == mappingproxy.get(0, default)

        assert mappingproxy.copy() == dictionary

        assert repr(mappingproxy).startswith("mappingproxy")


attributes = st.builds(attr.ib, default=st.just(attr.NOTHING) | st.integers())


alphabet = string.ascii_uppercase + string.ascii_lowercase
if sys.version_info.major == 2:
    alphabet = alphabet.decode('ascii')
identifiers = st.text(alphabet=alphabet, min_size=1, )
if sys.version_info.major == 2:
    identifiers = identifiers.map(operator.methodcaller("encode"))

identifiers = identifiers.filter(lambda i: not keyword.iskeyword(i))

classes = st.dictionaries(identifiers, attributes)


@classes.flatmap
def classes(attributes):
    """
    Generate ``attrs`` classes with the given attributes.
    """
    defaults_last = sorted(
        attributes.values(),
        key=lambda a: 0 if a._default == attr.NOTHING else 1,
    )
    for i, attribute in enumerate(defaults_last):
        attribute.counter = i
    return st.builds(attr.make_class, identifiers, st.just(attributes))


@attr.s(frozen=True)
class BuilderState(object):
    """
    State for :py:class:`TestBuilder`
    """
    cls = attr.ib()
    builder = attr.ib()
    possible = attr.ib()

    consumed = attr.ib(default=frozenset())

    def available_default(self):
        """
        Yield an available defaulted attributed for the wrapped class.
        """
        for attribute in self.possible - self.consumed:
            if attribute.default is not attr.NOTHING:
                yield attribute

    def available_required(self):
        """
        Yield the unconsumed required attributes for the wrapped
        class.
        """
        for attribute in self.possible - self.consumed:
            if attribute.default is attr.NOTHING:
                yield attribute


class BuilderStateMachine(RuleBasedStateMachine):
    """
    Tests for :py:func:`builder`.
    """
    starting = Bundle("starting")
    in_progress = Bundle("advanced")

    @rule(cls=classes, target=starting)
    def start(self, cls):
        return BuilderState(cls, builder(cls), frozenset(attr.fields(cls)))

    def add_argument(self, state, attribute):
        """
        Add an attribute to the state.

        :param state: A :py:class:`BuilderState` instance
        :param attribute: An :py:class:`attr.ib` instance.

        :return: A :py:class:`BuilderState` representing a builder
                 with the attribute added as an argument.
        """
        assume(attribute)
        method = getattr(state.builder, attribute.name)
        builder = method("value")
        return attr.evolve(
            state,
            builder=builder,
            consumed=state.consumed | {attribute},
        )

    @rule(started=starting | in_progress, target=in_progress)
    def add_free_required_argument_succeeds(self, started):
        """
        A free required argument can always be added to a builder.
        """
        free = next(iter(started.available_required()), None)
        return self.add_argument(started, free)

    @rule(started=starting | in_progress, target=in_progress)
    def add_unconsumed_defaulted_argument_succeed(self, started):
        """
        An unconsumed, unrequired argument (i.e., one with a default
        value) can always be added to a builder.
        """
        unconsumed = next(iter(started.available_default()), None)
        return self.add_argument(started, unconsumed)

    @rule(started=starting | in_progress)
    def add_unknown_argument_fails(self, started):
        """
        An unknown argument can never be added to a builder.
        """
        # The concatenation of all attribute names doubled cannot be
        # itself an attribute name.
        unknown = "".join(a.name for a in started.possible) * 2
        with pytest.raises(AttributeError):
            getattr(started.builder, unknown)

    @rule(started=in_progress)
    def add_consumed_argument_fails(self, started):
        """
        A consumed argument cannot be added.
        """
        consumed = next(iter(started.consumed), None)
        assume(consumed)

        with pytest.raises(ConsumedArgument):
            getattr(started.builder, consumed.name)

    @rule(maybe_finished=starting | in_progress)
    def build(self, maybe_finished):
        """
        A builder can only build a instance if all required arguments
        have been consumed.
        """
        if list(maybe_finished.available_required()):
            with pytest.raises(IncompleteArguments):
                maybe_finished.builder.build()
        else:
            assert isinstance(maybe_finished.builder.build(),
                              maybe_finished.cls)


TestBuilder = BuilderStateMachine.TestCase
