extends Control

const INK := Color("101b24")
const INK_SOFT := Color("172732")
const PAPER := Color("ece8dc")
const MUTED := Color("9aa9a9")
const COPPER := Color("d38b66")
const SAGE := Color("8ba99a")
const LINE := Color("35464f")

var _latest_event := ""
var _latest_path := ""
var _event_label: Label
var _path_label: Label
var _options_panel: Panel
var _continue_button: Button
var _journey_button: Button
var _settings_button: Button
var _toggle_button: Button
var _save_button: Button
var _back_button: Button
var _trace_file := ""
var _asset_dir := ""
var _frame_dir := ""
var _capture_names: Array[String] = []
var _capture_errors: Array[String] = []
var _seen_events: Array[String] = []


func _ready() -> void:
	custom_minimum_size = Vector2(1280, 720)
	PulseLiteUI.played.connect(_on_pulse_played)
	_trace_file = _argument_value("--trace-file=")
	_asset_dir = _argument_value("--asset-dir=")
	_frame_dir = _argument_value("--frame-dir=")
	if not _asset_dir.is_empty() or not _frame_dir.is_empty():
		# Capture runs are placed off the physical display and are not focusable.
		DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	if not _trace_file.is_empty():
		var trace := FileAccess.open(_trace_file, FileAccess.WRITE)
		if trace != null:
			trace.close()

	_build_interface()
	PulseLiteUI.wire_buttons(self)
	if not _asset_dir.is_empty() or not _frame_dir.is_empty():
		call_deferred("_run_capture_sequence")


func _draw() -> void:
	var band_count := 24
	var top := Color("101b24")
	var bottom := Color("172a32")
	for i in band_count:
		var ratio := float(i) / float(band_count - 1)
		var y0 := size.y * float(i) / float(band_count)
		var y1 := size.y * float(i + 1) / float(band_count)
		draw_rect(Rect2(0, y0, size.x, y1 - y0 + 1.0), top.lerp(bottom, ratio), true)

	# Restrained, hand-drawn horizon rings keep the menu from feeling like a flat template.
	draw_circle(Vector2(1055, 192), 240, Color("20343b"))
	draw_circle(Vector2(1055, 192), 239, Color("192b34"))
	draw_arc(Vector2(1055, 192), 238, deg_to_rad(205), deg_to_rad(340), 80, Color(0.74, 0.52, 0.37, 0.32), 1.0, true)
	draw_arc(Vector2(1055, 192), 211, deg_to_rad(210), deg_to_rad(335), 72, Color(0.57, 0.68, 0.62, 0.2), 1.0, true)
	draw_line(Vector2(716, 0), Vector2(716, 720), Color(0.75, 0.82, 0.76, 0.07), 1.0)
	for dot in [Vector2(108, 118), Vector2(620, 120), Vector2(1120, 94), Vector2(1160, 260), Vector2(684, 600), Vector2(1040, 666), Vector2(300, 671)]:
		draw_circle(dot, 1.5, Color(0.92, 0.78, 0.61, 0.52))


func _build_interface() -> void:
	_add_label(self, Vector2(76, 36), Vector2(310, 22), "NIGHTJAR / MENU STUDY", 13, SAGE, true)
	_add_label(self, Vector2(76, 59), Vector2(390, 20), "FREE-SAMPLE SOUND MAPPING", 10, MUTED, false)
	_add_label(self, Vector2(912, 45), Vector2(292, 24), "GODOT 4  /  LIVE SIGNAL CAPTIONS", 11, PAPER, true, HORIZONTAL_ALIGNMENT_RIGHT)

	_add_label(self, Vector2(84, 145), Vector2(560, 20), "01  /  A SMALL FICTIONAL GAME MENU", 12, COPPER, true)
	_add_label(self, Vector2(80, 178), Vector2(610, 154), "MIRROR\n& MIST", 64, PAPER, true)
	_add_label(self, Vector2(86, 344), Vector2(540, 30), "A quiet world, waiting on one clear input.", 17, MUTED, false)
	_draw_rule(Vector2(86, 395), 528)

	_continue_button = _add_button(Vector2(86, 420), Vector2(316, 52), "CONTINUE  /  CHAPTER 02", "standard")
	_journey_button = _add_button(Vector2(86, 483), Vector2(316, 52), "BEGIN A NEW JOURNEY", "primary")
	_journey_button.set_meta(&"pulselite_event", "menu_confirm")
	_settings_button = _add_button(Vector2(86, 546), Vector2(316, 52), "AUDIO SETTINGS", "standard")
	_settings_button.pressed.connect(_show_options)
	_add_label(self, Vector2(88, 622), Vector2(570, 20), "Illustrative interface only. The sound pack does not include a game UI.", 11, MUTED, false)

	_build_signal_panel()
	_build_event_map()
	_build_options_panel()


func _build_signal_panel() -> void:
	var panel := _add_panel(Vector2(760, 142), Vector2(444, 278), Color("172630"), Color("3b5056"))
	_add_label(panel, Vector2(24, 19), Vector2(370, 18), "PULSELITE / PLAYBACK RECEIPT", 11, SAGE, true)
	_add_label(panel, Vector2(24, 48), Vector2(390, 28), "Last sound event", 19, PAPER, true)
	_add_label(panel, Vector2(24, 91), Vector2(120, 16), "EVENT", 10, MUTED, true)
	_event_label = _add_label(panel, Vector2(24, 109), Vector2(390, 29), "No playback yet", 20, COPPER, true)
	_add_label(panel, Vector2(24, 153), Vector2(120, 16), "FILE", 10, MUTED, true)
	_path_label = _add_label(panel, Vector2(24, 174), Vector2(396, 27), "Waiting for PulseLiteUI.played", 14, PAPER, false)
	_draw_rule_in(panel, Vector2(24, 216), 396)
	_add_label(panel, Vector2(24, 231), Vector2(232, 18), "Signal: played(event, path)", 10, MUTED, false)
	_add_label(panel, Vector2(382, 231), Vector2(46, 18), "LIVE", 9, SAGE, true, HORIZONTAL_ALIGNMENT_RIGHT)
	# A quiet activity mark is decoration; event and file labels above are signal-fed.
	for i in 9:
		var bar := ColorRect.new()
		bar.position = Vector2(270 + i * 12, 241 - (i % 3) * 4)
		bar.size = Vector2(5, 7 + (i % 3) * 4)
		bar.color = Color(0.55, 0.68, 0.61, 0.5)
		panel.add_child(bar)


func _build_event_map() -> void:
	var panel := _add_panel(Vector2(760, 438), Vector2(444, 188), Color("172630"), Color("35484f"))
	_add_label(panel, Vector2(24, 18), Vector2(390, 20), "INPUTS IN THIS SCENE", 11, COPPER, true)
	_add_label(panel, Vector2(24, 46), Vector2(390, 21), "A real button signal, a matching sound caption.", 14, PAPER, false)
	var rows := [
		["HOVER", "button_hover"],
		["PRESS", "button_click"],
		["CONFIRM / BACK", "menu_confirm / menu_back"],
		["TOGGLE", "toggle_on / toggle_off"],
	]
	for i in rows.size():
		var y := 80 + i * 23
		_add_label(panel, Vector2(24, y), Vector2(140, 18), rows[i][0], 10, MUTED, true)
		_add_label(panel, Vector2(166, y), Vector2(250, 18), rows[i][1], 11, PAPER, false)


func _build_options_panel() -> void:
	_options_panel = _add_panel(Vector2(760, 438), Vector2(444, 188), Color("1d3038"), Color("557068"))
	_options_panel.visible = false
	_add_label(_options_panel, Vector2(24, 18), Vector2(390, 20), "AUDIO SETTINGS", 11, SAGE, true)
	_add_label(_options_panel, Vector2(24, 45), Vector2(390, 21), "A separate on/off sound for this switch.", 13, PAPER, false)

	_toggle_button = _add_button(Vector2(24, 82), Vector2(202, 48), "AMBIENCE  /  OFF", "toggle", _options_panel)
	_toggle_button.toggle_mode = true
	_toggle_button.button_pressed = false
	_toggle_button.toggled.connect(_update_toggle_caption)
	_add_label(_options_panel, Vector2(24, 143), Vector2(203, 17), "toggle_on  /  toggle_off", 10, MUTED, false)

	_save_button = _add_button(Vector2(242, 82), Vector2(88, 48), "SAVE", "small", _options_panel)
	_save_button.set_meta(&"pulselite_event", "menu_confirm")
	_back_button = _add_button(Vector2(338, 82), Vector2(82, 48), "BACK", "small", _options_panel)
	_back_button.set_meta(&"pulselite_event", "menu_back")
	_back_button.pressed.connect(_hide_options)
	_add_label(_options_panel, Vector2(242, 143), Vector2(178, 17), "confirm  /  back", 10, MUTED, false)


func _add_button(position_value: Vector2, size_value: Vector2, caption: String, style_name: String, parent: Control = null) -> Button:
	var button := Button.new()
	button.text = caption
	button.position = position_value
	button.size = size_value
	button.focus_mode = Control.FOCUS_ALL
	button.alignment = HORIZONTAL_ALIGNMENT_LEFT
	button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	button.add_theme_font_size_override("font_size", 13 if style_name == "small" else 14)
	button.add_theme_color_override("font_color", PAPER)
	button.add_theme_color_override("font_hover_color", Color("fff9eb"))
	button.add_theme_color_override("font_pressed_color", Color("fff9eb"))
	button.add_theme_color_override("font_focus_color", Color("fff9eb"))
	var palette := {
		"standard": [Color("1a2a33"), Color("233740"), Color("30464a"), Color("35494c")],
		"primary": [Color("a45f43"), Color("bf7654"), Color("854a36"), Color("d28a64")],
		"toggle": [Color("22343b"), Color("293f43"), Color("355047"), Color("547363")],
		"small": [Color("22343b"), Color("2a4147"), Color("354e50"), Color("55736b")],
	}
	var colors: Array = palette[style_name]
	button.add_theme_stylebox_override("normal", _button_box(colors[0], Color("40535a")))
	button.add_theme_stylebox_override("hover", _button_box(colors[1], Color("88a295")))
	button.add_theme_stylebox_override("pressed", _button_box(colors[2], Color("d38b66")))
	button.add_theme_stylebox_override("focus", _button_box(colors[3], Color("88a295")))
	if parent == null:
		add_child(button)
	else:
		parent.add_child(button)
	return button


func _button_box(fill: Color, outline: Color) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = fill
	box.border_color = outline
	box.set_border_width_all(1)
	box.set_corner_radius_all(9)
	box.content_margin_left = 18
	box.content_margin_right = 12
	box.content_margin_top = 8
	box.content_margin_bottom = 8
	return box


func _add_panel(position_value: Vector2, size_value: Vector2, fill: Color, outline: Color) -> Panel:
	var panel := Panel.new()
	panel.position = position_value
	panel.size = size_value
	var box := StyleBoxFlat.new()
	box.bg_color = fill
	box.border_color = outline
	box.set_border_width_all(1)
	box.set_corner_radius_all(13)
	box.content_margin_left = 0
	box.content_margin_right = 0
	box.content_margin_top = 0
	box.content_margin_bottom = 0
	panel.add_theme_stylebox_override("panel", box)
	add_child(panel)
	return panel


func _add_label(parent: Control, position_value: Vector2, size_value: Vector2, caption: String, font_size: int, color: Color, bold: bool, alignment: HorizontalAlignment = HORIZONTAL_ALIGNMENT_LEFT) -> Label:
	var label := Label.new()
	label.text = caption
	label.position = position_value
	label.size = size_value
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	label.horizontal_alignment = alignment
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.clip_text = true
	if bold:
		label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0))
	parent.add_child(label)
	return label


func _draw_rule(position_value: Vector2, width_value: float) -> void:
	var rule := ColorRect.new()
	rule.position = position_value
	rule.size = Vector2(width_value, 1)
	rule.color = Color(0.72, 0.8, 0.76, 0.22)
	add_child(rule)
	var dot := ColorRect.new()
	dot.position = position_value + Vector2(width_value - 2, -1)
	dot.size = Vector2(4, 4)
	dot.color = COPPER
	add_child(dot)


func _draw_rule_in(parent: Control, position_value: Vector2, width_value: float) -> void:
	var rule := ColorRect.new()
	rule.position = position_value
	rule.size = Vector2(width_value, 1)
	rule.color = Color(0.72, 0.8, 0.76, 0.22)
	parent.add_child(rule)


func _show_options() -> void:
	_options_panel.visible = true


func _hide_options() -> void:
	_options_panel.visible = false


func _update_toggle_caption(on: bool) -> void:
	_toggle_button.text = "AMBIENCE  /  ON" if on else "AMBIENCE  /  OFF"


func _on_pulse_played(event: StringName, path: String) -> void:
	_latest_event = String(event)
	_latest_path = path
	_seen_events.append(_latest_event)
	_event_label.text = _latest_event
	_path_label.text = path.replace("res://addons/pulselite_ui/sounds/", "")
	if not ResourceLoader.exists(path):
		_capture_errors.append("Signal referenced missing resource: %s" % path)

	if not _trace_file.is_empty():
		var trace := FileAccess.open(_trace_file, FileAccess.READ_WRITE)
		if trace == null:
			_capture_errors.append("Could not append private played-signal trace")
		else:
			trace.seek_end()
			trace.store_line(JSON.stringify({
				"elapsed_ms": Time.get_ticks_msec(),
				"event": _latest_event,
				"path": path,
				"resource_exists": ResourceLoader.exists(path),
			}))
			trace.close()


func _argument_value(prefix: String) -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(prefix):
			return argument.substr(prefix.length())
	return ""


func _run_capture_sequence() -> void:
	if _asset_dir.is_empty() or _frame_dir.is_empty() or _trace_file.is_empty():
		push_error("Capture mode requires --asset-dir, --frame-dir and --trace-file")
		get_tree().quit(2)
		return
	var capture_dir_error := DirAccess.make_dir_recursive_absolute(_frame_dir) if not _frame_dir.is_empty() else OK
	var asset_dir_error := DirAccess.make_dir_recursive_absolute(_asset_dir) if not _asset_dir.is_empty() else OK
	if capture_dir_error != OK or asset_dir_error != OK:
		_capture_errors.append("Could not create a requested output directory")

	await get_tree().create_timer(0.55).timeout
	await _capture_frame("frame-01-idle.png", "01-main-menu.png", "")

	await _move_mouse_to(_continue_button)
	await get_tree().create_timer(0.2).timeout
	await _capture_frame("frame-02-hover.png", "", "button_hover")

	await _click_button(_continue_button)
	await get_tree().create_timer(0.16).timeout
	await _capture_frame("frame-03-click.png", "", "button_click")

	await _click_button(_journey_button)
	await get_tree().create_timer(0.16).timeout
	await _capture_frame("frame-04-confirm.png", "02-confirm-signal.png", "menu_confirm")

	await _click_button(_settings_button)
	await get_tree().create_timer(0.16).timeout
	await _capture_frame("frame-05-options.png", "", "button_click")

	await _click_button(_toggle_button)
	await get_tree().create_timer(0.16).timeout
	await _capture_frame("frame-06-toggle-on.png", "03-options-toggle.png", "toggle_on")

	await _click_button(_toggle_button)
	await get_tree().create_timer(0.16).timeout
	await _capture_frame("frame-07-toggle-off.png", "", "toggle_off")

	await _click_button(_save_button)
	await get_tree().create_timer(0.16).timeout
	await _capture_frame("frame-08-save.png", "", "menu_confirm")

	await _click_button(_back_button)
	await get_tree().create_timer(0.16).timeout
	await _capture_frame("frame-09-back.png", "", "menu_back")

	var required := ["button_hover", "button_click", "menu_confirm", "menu_back", "toggle_on", "toggle_off"]
	for required_event in required:
		if not _seen_events.has(required_event):
			_capture_errors.append("Expected played event was not emitted: %s" % required_event)
	if _capture_names.size() != 9:
		_capture_errors.append("Expected nine Godot viewport frames, got %d" % _capture_names.size())
	if not _capture_errors.is_empty():
		for problem in _capture_errors:
			push_error("A027 capture: " + problem)
		print("A027_CAPTURE_FAIL events=%s captures=%d" % [JSON.stringify(_seen_events), _capture_names.size()])
		get_tree().quit(1)
		return
	print("A027_CAPTURE_OK engine=%s size=%s events=%s captures=%d" % [Engine.get_version_info().string, str(get_viewport_rect().size), JSON.stringify(_seen_events), _capture_names.size()])
	get_tree().quit(0)


func _move_mouse_to(button: Control) -> void:
	var motion := InputEventMouseMotion.new()
	motion.position = button.get_global_rect().get_center()
	motion.global_position = motion.position
	get_viewport().push_input(motion, true)
	await get_tree().create_timer(0.12).timeout


func _click_button(button: BaseButton) -> void:
	await _move_mouse_to(button)
	var point := button.get_global_rect().get_center()
	var press := InputEventMouseButton.new()
	press.button_index = MOUSE_BUTTON_LEFT
	press.pressed = true
	press.position = point
	press.global_position = point
	get_viewport().push_input(press, true)
	await get_tree().process_frame
	var release := InputEventMouseButton.new()
	release.button_index = MOUSE_BUTTON_LEFT
	release.pressed = false
	release.position = point
	release.global_position = point
	get_viewport().push_input(release, true)
	await get_tree().create_timer(0.12).timeout


func _capture_frame(frame_name: String, public_name: String, expected_event: String) -> void:
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	if image.is_empty() or image.get_width() != 1280 or image.get_height() != 720:
		_capture_errors.append("Unexpected viewport image dimensions for %s: %dx%d" % [frame_name, image.get_width(), image.get_height()])
		return
	if not expected_event.is_empty() and (_latest_event != expected_event or _event_label.text != expected_event):
		_capture_errors.append("Displayed played event mismatch at %s: latest=%s label=%s expected=%s" % [frame_name, _latest_event, _event_label.text, expected_event])
	if not _latest_path.is_empty() and _path_label.text != _latest_path.replace("res://addons/pulselite_ui/sounds/", ""):
		_capture_errors.append("Displayed audio path is not derived from the latest played signal")
	var frame_path := _frame_dir.path_join(frame_name)
	if image.save_png(frame_path) != OK:
		_capture_errors.append("Could not save rendered frame %s" % frame_path)
	else:
		_capture_names.append(frame_name)
	if not public_name.is_empty():
		var public_path := _asset_dir.path_join(public_name)
		if image.save_png(public_path) != OK:
			_capture_errors.append("Could not save public screenshot %s" % public_path)
