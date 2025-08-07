#!/usr/bin/env python3
#
#  __init__.py
"""
Parser and editor of project.godot files.
"""
#
#  Copyright © 2025 Dominic Davis-Foster <dominic@davis-foster.co.uk>
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#  DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#  OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
#  OR OTHER DEALINGS IN THE SOFTWARE.
#

__author__: str = "Dominic Davis-Foster"
__copyright__: str = "2025 Dominic Davis-Foster"
__license__: str = "MIT License"
__version__: str = "0.1.0"
__email__: str = "dominic@davis-foster.co.uk"

__all__ = ("loads", "load", "load_path", "dumps", "dump", "dump_to_path", "TOMLDecodeError")

# stdlib
from typing import TYPE_CHECKING, Any, Dict, Mapping

# 3rd party
from tomli._types import ParseFloat

# this package
from ._dump import dump, dumps
from ._parser import TOMLDecodeError, load, loads

if TYPE_CHECKING:
	# 3rd party
	from domdf_python_tools.typing import PathLike


def load_path(path: "PathLike", *, parse_float: ParseFloat = float) -> Dict[str, Any]:
	"""
	Parse ``project.godot`` from the given path.

	:param path:
	:param parse_float:
	"""

	with open(path, "rb") as fp:
		return load(fp, parse_float=parse_float)


def dump_to_path(obj: Mapping[str, Any], path: "PathLike") -> None:
	"""
	Reconstruct a ``project.godot`` file and write to the given path.

	:param obj:
	:param path:
	"""

	with open(path, "wb") as fp:
		dump(obj, fp)
