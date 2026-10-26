extends Control

const VIDEO_INTERVAL_SECONDS := 0.1
const DEFAULT_VIDEO_SECONDS := 15.0

var _demo_root: Control
var _video_output_dir := ""
var _pack_label := ""
var _video_seconds := DEFAULT_VIDEO_SECONDS
var _capture_fps := 10.0
var _recording := false
var _capture_busy := false
var _frame_index := 0
var _next_frame_seconds := 0.0
var _capture_errors: Array[String] = []
var _seen_events: Array[String] = []
var _event_counts: Dictionary = {}
var _started_at_msec := 0


func _ready() -> void:
	custom_minimum_size = Vector2(1280, 720)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	_video_output_dir = _argument_value("--video-output-dir=")
	_pack_label = _argument_value("--pack-label=")
	if _pack_label.is_empty():
		_pack_label = "Audio pack"
	var duration_argument := _argument_value("--video-seconds=")
	if not duration_argument.is_empty():
		_video_seconds = clampf(duration_argument.to_float(), 12.0, 20.0)
	var fps_argument := _argument_value("--video-fps=")
	if not fps_argument.is_empty():
		_capture_fps = clampf(fps_argument.to_float(), 6.0, 15.0)
	if _video_output_dir.is_empty():
		push_error("Video capture requires --video-output-dir")
		get_tree().quit(2)
		return
	var dir_error := DirAccess.make_dir_recursive_absolute(_video_output_dir)
	if dir_error != OK:
		push_error("Could not create the private video-frame directory")
		get_tree().quit(2)
		return

	var demo_scene := load("res://marketing/visuals/demo.tscn") as PackedScene
	if demo_scene == null:
		push_error("Could not load the existing PulseLite demo scene")
		get_tree().quit(2)
		return
	_demo_root = demo_scene.instantiate() as Control
	if _demo_root == null:
		push_error("The existing PulseLite demo scene did not instantiate as a Control")
		get_tree().quit(2)
		return
	_demo_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(_demo_root)
	_install_pack_labels()
	PulseLiteUI.played.connect(_on_played)
	call_deferred("_run_input_sequence")


func _process(delta: float) -> void:
	if not _recording or _capture_busy:
		return
	_next_frame_seconds -= delta
	if _next_frame_seconds <= 0.0:
		_next_frame_seconds += 1.0 / _capture_fps
		_capture_busy = true
		call_deferred("_capture_frame")


func _install_pack_labels() -> void:
	var header := _find_label_with_text(_demo_root, "GODOT 4  /  LIVE SIGNAL CAPTIONS")
	if header != null:
		header.text = "%s / LIVE SIGNAL CAPTIONS" % _pack_label.to_upper()
	var badge := Label.new()
	badge.text = "ILLUSTRATIVE EXAMPLE / %s SOUND PACK" % _pack_label.to_upper()
	badge.position = Vector2(76, 92)
	badge.size = Vector2(610, 20)
	badge.add_theme_font_size_override("font_size", 11)
	badge.add_theme_color_override("font_color", Color("d38b66"))
	badge.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_demo_root.add_child(badge)


func _find_label_with_text(node: Node, target: String) -> Label:
	if node is Label and (node as Label).text == target:
		return node as Label
	for child in node.get_children():
		var result := _find_label_with_text(child, target)
		if result != null:
			return result
	return null


func _find_button(prefix: String) -> Button:
	return _find_button_recursive(_demo_root, prefix)


func _find_button_recursive(node: Node, prefix: String) -> Button:
	if node is Button and (node as Button).text.begins_with(prefix):
		return node as Button
	for child in node.get_children():
		var result := _find_button_recursive(child, prefix)
		if result != null:
			return result
	return null


func _run_input_sequence() -> void:
	await get_tree().process_frame
	await get_tree().create_timer(0.35).timeout
	var continue_button := _find_button("CONTINUE")
	var journey_button := _find_button("BEGIN A NEW JOURNEY")
	var settings_button := _find_button("AUDIO SETTINGS")
	if continue_button == null or journey_button == null or settings_button == null:
		_capture_errors.append("Could not find the expected menu buttons")
		_finish_capture(1)
		return

	await _move_mouse_to(continue_button)
	_started_at_msec = Time.get_ticks_msec()
	_next_frame_seconds = 0.0
	_recording = true
	await get_tree().create_timer(0.7).timeout
	await _click_button(continue_button)
	await get_tree().create_timer(1.05).timeout
	await _click_button(journey_button)
	await get_tree().create_timer(1.05).timeout
	await _click_button(settings_button)
	await get_tree().create_timer(0.65).timeout
	var toggle_button := _find_button("AMBIENCE")
	var save_button := _find_button("SAVE")
	var back_button := _find_button("BACK")
	if toggle_button == null or save_button == null or back_button == null:
		_capture_errors.append("Could not find the expected settings buttons")
		_finish_capture(1)
		return

	await _click_button(toggle_button)
	await get_tree().create_timer(1.05).timeout
	await _click_button(toggle_button)
	await get_tree().create_timer(1.05).timeout
	await _click_button(save_button)
	await get_tree().create_timer(1.05).timeout
	await _click_button(back_button)

	var elapsed := float(Time.get_ticks_msec() - _started_at_msec) / 1000.0
	if elapsed < _video_seconds:
		await get_tree().create_timer(_video_seconds - elapsed).timeout
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	while _capture_busy:
		await get_tree().process_frame
	_finish_capture(0)


func _move_mouse_to(button: Control) -> void:
	var point := button.get_global_rect().get_center()
	var motion := InputEventMouseMotion.new()
	motion.position = point
	motion.global_position = point
	get_viewport().push_input(motion, true)
	await get_tree().create_timer(0.16).timeout


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
	await get_tree().create_timer(0.16).timeout


func _capture_frame() -> void:
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	if image.is_empty() or image.get_width() != 1280 or image.get_height() != 720:
		_capture_errors.append("Unexpected Godot viewport dimensions: %dx%d" % [image.get_width(), image.get_height()])
	else:
		var frame_path := _video_output_dir.path_join("frame-%05d.png" % _frame_index)
		if image.save_png(frame_path) != OK:
			_capture_errors.append("Could not save a Godot viewport frame")
		else:
			_frame_index += 1
	_capture_busy = false


func _on_played(event: StringName, path: String) -> void:
	var event_name := String(event)
	_seen_events.append(event_name)
	_event_counts[event_name] = int(_event_counts.get(event_name, 0)) + 1
	if not ResourceLoader.exists(path):
		_capture_errors.append("Played signal referred to a missing resource: %s" % path)


func _finish_capture(initial_status: int) -> void:
	_recording = false
	var required := ["button_hover", "button_click", "menu_confirm", "menu_back", "toggle_on", "toggle_off"]
	for required_event in required:
		if not _seen_events.has(required_event):
			_capture_errors.append("Expected played event was not emitted: %s" % required_event)
	if _frame_index < int(_video_seconds * _capture_fps * 0.75):
		_capture_errors.append("Too few captured viewport frames: %d" % _frame_index)
	var status := initial_status
	if not _capture_errors.is_empty():
		status = 1
		for problem in _capture_errors:
			push_error("Video capture: " + problem)
		print("VIDEO_CAPTURE_FAIL pack=%s frames=%d events=%s" % [_pack_label, _frame_index, JSON.stringify(_event_counts)])
	else:
		print("VIDEO_CAPTURE_OK pack=%s engine=%s size=%s fps=%.1f frames=%d events=%s" % [
			_pack_label,
			Engine.get_version_info().string,
			str(get_viewport_rect().size),
			_capture_fps,
			_frame_index,
			JSON.stringify(_event_counts),
		])
	get_tree().quit(status)


func _argument_value(prefix: String) -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(prefix):
			return argument.substr(prefix.length())
	return ""
