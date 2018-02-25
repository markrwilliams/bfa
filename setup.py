import ast
import os
from setuptools import setup, find_packages

META_PATH = os.path.join(
    os.path.dirname(__file__),
    "src", "bfa", "__init__.py",
)


class CollectMetadata(ast.NodeVisitor):
    """
    Collect metadata from a Python module.
    """

    @classmethod
    def frompath(cls, path):
        """
        Load metadata from the specified path.

        :param path: A path on the filesystem.
        :type path: :py:class:`str`

        :return: :py:class:`CollectMetadata`
        """
        metadata = cls(path)
        with open(path) as f:
            metadata.visit(ast.parse(f.read(), META_PATH))
        return metadata

    def __init__(self, path):
        self._path = path
        self._assignments = {}

    def visit_Assign(self, assign):
        """
        Record assignments of strings to names.

        :param assign: An ``Assign`` node.
        """
        for target in assign.targets:
            if (isinstance(target, ast.Name) and
                isinstance(assign.value, ast.Str)):
                self._assignments[target.id] = assign.value.s

    def get(self, name):
        """
        Retrieve the value for ``name`` from assignments.

        :param name: The metadata key.
        :type name: :py:class:`str`.
        """
        try:
            return self._assignments[name]
        except KeyError:
            raise RuntimeError(
                "Could not find {} in {}".format(name, self._path))


metadata = CollectMetadata.frompath(META_PATH)

setup(
    use_incremental=True,
    setup_requires=["incremental"],
    name="bfa",
    description=metadata.get("__description__"),
    author=metadata.get("__author__"),
    author_email=metadata.get("__email__"),
    maintainer=metadata.get("__author__"),
    maintainer_email=metadata.get("__email__"),
    license=metadata.get("__license__"),
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=[
        "attrs",
        "incremental",
    ],
    extras_require={
        "docs": ["sphinx"],
        "dev": [
            "click",
            "coverage",
            "Hypothesis",
            "pytest",
            "tox",
            "Twisted",
        ]
    }
)
