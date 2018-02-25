from ._implementation import ConsumedArgument, IncompleteArguments, builder
from ._version import __version__


__all__ = ["builder", "ConsumedArgument", "IncompleteArguments", "__version__"]

__title__ = "bfa"
__description__ = """
bfa - Builders For ``attrs``
============================

``bfa`` implements the builder pattern for ``attrs``-decorated
classes.  Use it to incrementally construct a ``frozen`` class.
"""
__uri__ = "http://bfa.readthedocs.io/"
__doc__ = __description__ + "\n<" + __uri__ + ">"


__author__ = "Mark Williams"
__email__ = "mrw@enotuniq.org"

__license__ = "MIT"
__copyright__ = "Copyright (c) 2018 Mark Williams"
