# stdlib
import dataclasses
from typing import Callable, Type, TypeVar

# 3rd party
from pytest_regressions.data_regression import RegressionYamlDumper

# this package
from godot_project_parser.types import GodotObject, PackedStringArray

pytest_plugins = ("coincidence", )

_C = TypeVar("_C", bound=Callable)


def _representer_for(*data_type: Type):  # noqa: MAN002

	def deco(representer_fn: _C) -> _C:
		for dtype in data_type:
			RegressionYamlDumper.add_custom_yaml_representer(dtype, representer_fn)

		return representer_fn

	return deco


@_representer_for(PackedStringArray)
def _represent_sequences(dumper: RegressionYamlDumper, data):  # noqa: MAN001,MAN002
	return dumper.represent_list(list(data))


@_representer_for(GodotObject)
def _represent_dataclasses(dumper: RegressionYamlDumper, data):  # noqa: MAN001,MAN002
	return dumper.represent_dict(dataclasses.asdict(data))
