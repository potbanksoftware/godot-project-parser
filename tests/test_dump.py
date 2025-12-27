# stdlib
from typing import Dict

# 3rd party
import pytest
from coincidence.regressions import AdvancedFileRegressionFixture

# this package
from godot_project_parser import dumps
from godot_project_parser.types import GodotObject, PackedStringArray

interact_events = [
		GodotObject(
				name="InputEventKey",
				kwargs={
						"resource_local_to_scene": False,
						"resource_name": '',
						"device": -1,
						"window_id": 0,
						"alt_pressed": False,
						"shift_pressed": False,
						"ctrl_pressed": False,
						"meta_pressed": False,
						"pressed": False,
						"keycode": 0,
						"physical_keycode": 69,
						"key_label": 0,
						"unicode": 101,
						"location": 0,
						"echo": False,
						"script": None,
						}
				),
		GodotObject(
				name="InputEventJoypadButton",
				kwargs={
						"resource_local_to_scene": False,
						"resource_name": '',
						"device": -1,
						"button_index": 2,
						"pressure": 0.0,
						"pressed": True,
						"script": None,
						}
				)
		]
jump_events = [
		GodotObject(
				name="InputEventJoypadButton",
				kwargs={
						"resource_local_to_scene": False,
						"resource_name": '',
						"device": -1,
						"button_index": 0,
						"pressure": 0.0,
						"pressed": True,
						"script": None,
						}
				),
		GodotObject(
				name="InputEventKey",
				kwargs={
						"resource_local_to_scene": False,
						"resource_name": '',
						"device": -1,
						"window_id": 0,
						"alt_pressed": False,
						"shift_pressed": False,
						"ctrl_pressed": False,
						"meta_pressed": False,
						"pressed": False,
						"keycode": 0,
						"physical_keycode": 32,
						"key_label": 0,
						"unicode": 32,
						"location": 0,
						"echo": False,
						"script": None,
						}
				)
		]
input_dict = {
		"input": {
				"interact": {"deadzone": 0.5, "events": interact_events},
				"jump": {"deadzone": 0.5, "events": jump_events},
				}
		}


@pytest.mark.parametrize(
		"data",
		[
				pytest.param({}, id="empty-dict"),
				pytest.param({
						"rendering": {
								"renderer/rendering_method": "gl_compatibility",
								"renderer/rendering_method.mobile": "gl_compatibility",
								"textures/canvas_textures/default_texture_filter": 0,
								}
						},
								id="rendering"),
				pytest.param({
						"layer_names": {
								"2d_physics/layer_1": "Floor/Obstruction",
								"2d_physics/layer_2": "Deer Back",
								"2d_physics/layer_3": "Obstacle Bounce",
								"2d_physics/layer_4": "Interaction",
								"2d_physics/layer_5": "Trees",
								"2d_physics/layer_6": "Pushables",
								"2d_physics/layer_7": "Fox Back",
								},
						},
								id="layer-names"),
				pytest.param(input_dict, id="input"),
				pytest.param({
						"editor_plugins": {
								"enabled":
										PackedStringArray([
												"res://addons/AutoExportVersion/plugin.cfg",
												"res://addons/debug_menu/plugin.cfg",
												"res://addons/godot-helpers/plugin.cfg",
												])
								},
						},
								id="editor-plugins"),
				pytest.param({
						"display": {"window/size/viewport_height": 1080, "window/size/viewport_width": 1920},
						},
								id="display"),
				pytest.param({
						"debug": {
								"gdscript/warnings/exclude_addons": False,
								"gdscript/warnings/untyped_declaration": 1,
								},
						},
								id="debug"),
				pytest.param({"foo": "abc", "bar": 123}, id="top-level-keys"),
				pytest.param({
						"autoload": {
								"AmbientMusicPlayer": "*res://addons/godot-helpers/ambient_music_player.gd",
								"Controller": "*res://addons/godot-helpers/controller/controller.gd",
								"DebugMenu": "*res://addons/debug_menu/debug_menu.tscn",
								"GodotHelpersUtils": "*res://addons/godot-helpers/utils.gd",
								"HUD": "*res://modules/hud/hud.tscn",
								"LevelManager": "*res://modules/shared/level_manager.gd",
								"Switcher": "*res://modules/switcher.gd",
								}
						},
								id="autoload"),
				pytest.param({"audio": {"general/default_playback_type.web": 0}}, id="audio"),
				pytest.param({
						"application": {
								"boot_splash/fullsize": False,
								"boot_splash/image": "res://art/boot-splash.png",
								"boot_splash/image.editor_hint": '',
								"boot_splash/minimum_display_time": 3000,
								"config/features": PackedStringArray(["4.3", "GL Compatibility"]),
								"config/icon": "res://art/icon/icon.png",
								"config/name": "Size Matters",
								"config/version": "Commit 3b468ca (master)",
								"run/main_scene": "res://levels/main_menu.tscn",
								}
						},
								id="application"),
				pytest.param({
						"addons": {
								"AutoExportVersion/version_config_file":
										"res://addons/AutoExportVersion/auto_export_version_config_file.gd"
								}
						},
								id="addons"),
				]
		)
def test_dumps(data: Dict, advanced_file_regression: AdvancedFileRegressionFixture) -> None:
	output = dumps(data)

	advanced_file_regression.check(output)
