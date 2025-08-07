# 3rd party
from coincidence.regressions import AdvancedFileRegressionFixture
from domdf_python_tools.paths import PathPlus

# this package
from godot_project_parser import dump_to_path, load_path


def test_roundtrip(tmp_pathplus: PathPlus, advanced_file_regression: AdvancedFileRegressionFixture) -> None:
	project_file = PathPlus(__file__).parent / "project.godot"

	data = load_path(project_file)

	dump_to_path(data, tmp_pathplus / "project.godot.output")

	advanced_file_regression.check_file(tmp_pathplus / "project.godot.output")
