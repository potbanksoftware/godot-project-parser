# stdlib
import os

# 3rd party
import pytest
from coincidence.regressions import AdvancedDataRegressionFixture
from domdf_python_tools.paths import PathPlus

# this package
from godot_project_parser import load, load_path, loads


def test_load_path(advanced_data_regression: AdvancedDataRegressionFixture) -> None:
	project_file = PathPlus(__file__).parent / "project.godot"

	advanced_data_regression.check(load_path(project_file))


def test_load(advanced_data_regression: AdvancedDataRegressionFixture) -> None:
	path = os.path.join(os.path.abspath(os.path.join(__file__, "..")), "project.godot")

	with open(path, "rb") as fp:
		advanced_data_regression.check(load(fp))


def test_loads(advanced_data_regression: AdvancedDataRegressionFixture) -> None:
	project_file = PathPlus(__file__).parent / "project.godot"

	advanced_data_regression.check(loads(project_file.read_text()))


def test_load_errors(tmp_pathplus: PathPlus):
	(tmp_pathplus / "foo").touch()

	with (tmp_pathplus / "foo").open('r') as fp:
		with pytest.raises(TypeError, match="File must be opened in binary mode"):
			load(fp)

	with pytest.raises(TypeError, match="Expected str object, not"):
		loads(b"abc")  # type: ignore[arg-type]
