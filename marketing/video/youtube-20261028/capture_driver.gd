extends Control

const CAPTURE_FPS := 8.0
const REQUIRED_UI_EVENTS := ["button_hover", "button_click", "menu_confirm", "menu_back", "toggle_on", "toggle_off"]
const MENU_EVENTS := [
	"button_click", "button_hover", "toggle_on", "toggle_off", "menu_confirm", "menu_back",
	"error", "notification", "panel_open", "panel_close", "transition", "coin_pickup", "reward", "level_up"
]

var _mode := "ui"
var _pack_label := "PulseLite"
var _duration_seconds := 20.0
var _frame_dir := ""
var _trace_path := ""
var _audio_path := ""
var _demo: Control
var _recording := false
var _capture_busy := false
var _next_frame_ms := 0
var _frame_index := 0
var _start_ms := 0
var _seen_events: Array[String] = []
var _errors: Array[String] = []
var _recorder: AudioEffectRecord


func _ready() -> void:
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	_mode = _argument_value("--mode=")
	_pack_label = _argument_value("--pack-label=")
	_duration_seconds = _argument_value("--duration=").to_float()
	_frame_dir = _argument_value("--yt-frame-dir=")
	_trace_path = _argument_value("--yt-trace-file=")
	_audio_path = _argument_value("--yt-audio-file=")
	if _duration_seconds <= 0.0 or _frame_dir.is_empty() or _trace_path.is_empty() or _audio_path.is_empty():
		push_error("Capture requires duration, frame directory, trace file, and audio file")
		get_tree().quit(2)
		return
	if not DirAccess.dir_exists_absolute(_frame_dir):
		var mkdir_result := DirAccess.make_dir_recursive_absolute(_frame_dir)
		if mkdir_result != OK:
			push_error("Could not create frame directory")
			get_tree().quit(2)
			return
	var trace := FileAccess.open(_trace_path, FileAccess.WRITE)
	if trace == null:
		push_error("Could not create event trace")
		get_tree().quit(2)
		return
	trace.close()
	var demo_scene := load("res://marketing/visuals/demo.tscn") as PackedScene
	if demo_scene == null:
		push_error("Could not load the existing illustrative Godot UI")
		get_tree().quit(2)
		return
	_demo = demo_scene.instantiate() as Control
	_demo.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(_demo)
	var old_title := _find_label(_demo, "FREE-SAMPLE SOUND MAPPING")
	if old_title != null:
		old_title.text = "%s SOUND MAPPING" % _pack_label.to_upper()
	PulseLiteUI.played.connect(_on_played)
	_recorder = AudioEffectRecord.new()
	AudioServer.add_bus_effect(AudioServer.get_bus_index("Master"), _recorder)
	call_deferred("_run_capture")


func _process(_delta: float) -> void:
	if not _recording or _capture_busy:
		return
	var elapsed_ms := Time.get_ticks_msec() - _start_ms
	if elapsed_ms >= _next_frame_ms:
		_next_frame_ms += int(1000.0 / CAPTURE_FPS)
		_capture_busy = true
		call_deferred("_capture_frame")


func _run_capture() -> void:
	await get_tree().process_frame
	await get_tree().create_timer(0.45).timeout
	_recorder.set_recording_active(true)
	_start_ms = Time.get_ticks_msec()
	_recording = true
	_next_frame_ms = 0
	if _mode == "menu14":
		await _run_menu_events()
	else:
		await _run_ui_sequence()
	var remaining := _duration_seconds - float(Time.get_ticks_msec() - _start_ms) / 1000.0
	if remaining > 0.0:
		await get_tree().create_timer(remaining).timeout
	_recording = false
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	while _capture_busy:
		await get_tree().process_frame
	_recorder.set_recording_active(false)
	var captured := _recorder.get_recording() as AudioStreamWAV
	if captured == null or captured.data.is_empty():
		_errors.append("AudioEffectRecord returned no waveform")
	else:
		var save_result := captured.save_to_wav(_audio_path)
		if save_result != OK:
			_errors.append("AudioEffectRecord could not save the captured WAV")
	var expected_count := MENU_EVENTS.size() if _mode == "menu14" else REQUIRED_UI_EVENTS.size()
	if _mode == "menu14":
		for event_name in MENU_EVENTS:
			if not _seen_events.has(event_name):
				_errors.append("Missing mapped Menu event: " + event_name)
	else:
		for event_name in REQUIRED_UI_EVENTS:
			if not _seen_events.has(event_name):
				_errors.append("Missing UI signal event: " + event_name)
	if _frame_index < int(_duration_seconds * CAPTURE_FPS * 0.75):
		_errors.append("Too few viewport frames: %d" % _frame_index)
	if not _errors.is_empty():
		for problem in _errors:
			push_error("YouTube capture: " + problem)
		print("YOUTUBE_CAPTURE_FAIL pack=%s events=%d frames=%d" % [_pack_label, _seen_events.size(), _frame_index])
		get_tree().quit(1)
		return
	print("YOUTUBE_CAPTURE_OK engine=%s pack=%s mode=%s duration=%.1f fps=%.1f frames=%d events=%s audio_bytes=%d" % [
		Engine.get_version_info().string, _pack_label, _mode, _duration_seconds, CAPTURE_FPS,
		_frame_index, JSON.stringify(_seen_events), captured.data.size()
	])
	get_tree().quit(0)


func _run_ui_sequence() -> void:
	var continue_button := _find_button("CONTINUE")
	var journey_button := _find_button("BEGIN A NEW JOURNEY")
	var settings_button := _find_button("AUDIO SETTINGS")
	if continue_button == null or journey_button == null or settings_button == null:
		_errors.append("Could not find the expected menu controls")
		return
	await _move_mouse_to(continue_button)
	await get_tree().create_timer(0.35).timeout
	await _click_button(continue_button)
	await get_tree().create_timer(0.8).timeout
	await _click_button(journey_button)
	await get_tree().create_timer(0.8).timeout
	await _click_button(settings_button)
	await get_tree().create_timer(0.45).timeout
	var toggle_button := _find_button("AMBIENCE")
	var save_button := _find_button("SAVE")
	var back_button := _find_button("BACK")
	if toggle_button == null or save_button == null or back_button == null:
		_errors.append("Could not find the expected settings controls")
		return
	await _click_button(toggle_button)
	await get_tree().create_timer(0.8).timeout
	await _click_button(toggle_button)
	await get_tree().create_timer(0.8).timeout
	await _click_button(save_button)
	await get_tree().create_timer(0.8).timeout
	await _click_button(back_button)


func _run_menu_events() -> void:
	# One signal-backed play per mapped event, at an even pace inside a 52 second take.
	for index in MENU_EVENTS.size():
		var target_seconds := 1.2 + float(index) * 3.55
		var remaining := target_seconds - float(Time.get_ticks_msec() - _start_ms) / 1000.0
		if remaining > 0.0:
			await get_tree().create_timer(remaining).timeout
		var player := PulseLiteUI.play(StringName(MENU_EVENTS[index]))
		if player == null:
			_errors.append("PulseLiteUI.play returned null for " + MENU_EVENTS[index])
		await get_tree().create_timer(0.18).timeout


func _move_mouse_to(button: Control) -> void:
	var point := button.get_global_rect().get_center()
	var motion := InputEventMouseMotion.new()
	motion.position = point
	motion.global_position = point
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
	await get_tree().create_timer(0.14).timeout


func _capture_frame() -> void:
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	if image.is_empty() or image.get_width() != 1280 or image.get_height() != 720:
		_errors.append("Unexpected viewport size at frame %d" % _frame_index)
	else:
		var path := _frame_dir.path_join("frame-%05d.png" % _frame_index)
		if image.save_png(path) != OK:
			_errors.append("Could not save viewport frame %d" % _frame_index)
		else:
			_frame_index += 1
	_capture_busy = false


func _on_played(event: StringName, path: String) -> void:
	var event_text := String(event)
	_seen_events.append(event_text)
	var resource_exists := ResourceLoader.exists(path)
	if not resource_exists:
		_errors.append("played signal reported missing resource: " + path)
	var trace := FileAccess.open(_trace_path, FileAccess.READ_WRITE)
	if trace == null:
		_errors.append("Could not open trace for appending")
		return
	trace.seek_end()
	trace.store_line(JSON.stringify({
		"elapsed_ms": Time.get_ticks_msec() - _start_ms if _start_ms > 0 else 0,
		"event": event_text,
		"path": path,
		"resource_exists": resource_exists,
	}))
	trace.close()


func _find_label(node: Node, caption: String) -> Label:
	if node is Label and (node as Label).text == caption:
		return node as Label
	for child in node.get_children():
		var found := _find_label(child, caption)
		if found != null:
			return found
	return null


func _find_button(prefix: String) -> Button:
	return _find_button_recursive(_demo, prefix)


func _find_button_recursive(node: Node, prefix: String) -> Button:
	if node is Button and (node as Button).text.begins_with(prefix):
		return node as Button
	for child in node.get_children():
		var found := _find_button_recursive(child, prefix)
		if found != null:
			return found
	return null


func _argument_value(prefix: String) -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(prefix):
			return argument.substr(prefix.length())
	return ""
