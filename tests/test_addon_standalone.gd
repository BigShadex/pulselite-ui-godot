extends SceneTree

const ADDON_SCRIPT := "res://addons/pulselite_ui/PulseLiteUI.gd"

var failures: Array[String] = []
var checks: int = 0
var played_events: Array[StringName] = []
var played_paths: Array[String] = []


func _initialize() -> void:
	call_deferred("_run")


func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)
		printerr("FAIL: ", message)


func _on_played(event: StringName, path: String) -> void:
	played_events.append(event)
	played_paths.append(path)


func check_last_play(event: StringName, suffix: String, context: String) -> void:
	check(not played_events.is_empty(), context + " emits played")
	if played_events.is_empty():
		return
	check(played_events.back() == event, context + " emits the expected event")
	check(played_paths.back().ends_with(suffix), context + " emits the expected sound path")


func _run() -> void:
	var player: Node = root.get_node_or_null("PulseLiteUI")
	check(player != null, "the project autoload registers PulseLiteUI")
	if player == null:
		finish()
		return

	var script: Script = player.get_script()
	check(script != null and script.resource_path == ADDON_SCRIPT,
		"the autoload uses the standalone addon script")
	check(player.has_signal("played"), "the autoload exposes its played signal")
	check(player.connect(&"played", _on_played) == OK, "the played signal can be observed")
	player.set("random_variation", false)
	player.set("hover_cooldown_ms", 0)
	check(player.get("bus") == &"UI", "UI is the default audio bus")

	var controls := VBoxContainer.new()
	var click_button := Button.new()
	var override_button := Button.new()
	var ignored_button := Button.new()
	var toggle_button := CheckButton.new()
	override_button.set_meta(&"pulselite_event", "menu_back")
	ignored_button.set_meta(&"pulselite_ignore", true)
	controls.add_child(click_button)
	controls.add_child(override_button)
	controls.add_child(ignored_button)
	controls.add_child(toggle_button)
	root.add_child(controls)
	await process_frame

	player.call("wire_buttons", controls)
	player.call("wire_buttons", controls)
	played_events.clear()
	played_paths.clear()
	click_button.pressed.emit()
	check(played_events.size() == 1, "repeated wire_buttons calls keep one pressed callback")
	check_last_play(&"button_click", "click/click_03.wav", "a normal button press")

	played_events.clear()
	played_paths.clear()
	click_button.mouse_entered.emit()
	check_last_play(&"button_hover", "hover/hover_01.wav", "a button hover")

	played_events.clear()
	played_paths.clear()
	override_button.pressed.emit()
	check_last_play(&"menu_back", "back_cancel/back_cancel_01.wav", "a metadata override")

	played_events.clear()
	played_paths.clear()
	ignored_button.pressed.emit()
	check(played_events.is_empty(), "pulselite_ignore suppresses the button sound")

	played_events.clear()
	played_paths.clear()
	toggle_button.toggled.emit(true)
	check_last_play(&"toggle_on", "toggle/toggle_01.wav", "a toggle-on signal")
	played_events.clear()
	played_paths.clear()
	toggle_button.toggled.emit(false)
	check_last_play(&"toggle_off", "toggle/toggle_02.wav", "a toggle-off signal")

	var voice: AudioStreamPlayer = player.call("play", &"menu_confirm", 2.5)
	check(voice != null, "play returns an audio player for a known event")
	if voice != null:
		check(voice.stream != null, "play returns a player with a loaded stream")
		check(voice.playing, "play starts the returned player")
		check(voice.bus == &"Master", "an unavailable default UI bus falls back to Master")
		player.set("volume_db", -8.0)
		voice = player.call("play", &"menu_confirm", 2.5)
		check(voice != null and is_equal_approx(voice.volume_db, -5.5),
			"volume_db and the per-play offset combine")

	var test_bus := StringName("PulseLiteTestBus_%s" % OS.get_process_id())
	AudioServer.add_bus()
	var test_bus_index := AudioServer.get_bus_count() - 1
	AudioServer.set_bus_name(test_bus_index, test_bus)
	player.set("bus", test_bus)
	voice = player.call("play", &"menu_confirm")
	check(voice != null and voice.bus == test_bus, "play selects an available named bus")

	var event_count_before_invalid := played_events.size()
	voice = player.call("play", &"not_a_pulselite_event")
	check(voice == null, "an unknown event safely returns null")
	check(played_events.size() == event_count_before_invalid,
		"an unknown event does not emit played")

	# The missing-file case uses a fresh, isolated node because base_path is a
	# before-first-play setting. The main signal and button checks above use the
	# actual registered PulseLiteUI autoload.
	var missing_file_player: Node = script.new()
	missing_file_player.set("base_path", "res://__pulselite_missing_fixture__/")
	root.add_child(missing_file_player)
	await process_frame
	check(missing_file_player.connect(&"played", _on_played) == OK,
		"the isolated missing-file fixture exposes its played signal")
	var event_count_before_missing := played_events.size()
	voice = missing_file_player.call("play", &"reward")
	check(voice == null, "a known event with no matching file safely returns null")
	check(played_events.size() == event_count_before_missing,
		"a missing file does not emit played")

	player.call("stop_all")
	missing_file_player.call("stop_all")
	await create_timer(0.1).timeout
	for child in player.get_children():
		if child is AudioStreamPlayer:
			check(not child.playing, "stop_all stops every voice before teardown")
	for child in missing_file_player.get_children():
		if child is AudioStreamPlayer:
			check(not child.playing, "the isolated missing-file fixture has no active voices")
	check(AudioServer.get_bus_index(test_bus) != -1,
		"the named audio bus remains valid through playback teardown")
	AudioServer.remove_bus(test_bus_index)
	player.set("bus", &"UI")
	player.set("volume_db", 0.0)
	voice = null
	controls.free()
	missing_file_player.free()
	player.free()
	script = null
	controls = null
	missing_file_player = null
	player = null
	await create_timer(0.1).timeout
	finish()


func finish() -> void:
	if failures.is_empty():
		print("PASS standalone: ", checks, " native assertions with the real PulseLiteUI autoload")
		call_deferred("quit", 0)
	else:
		printerr(failures.size(), " / ", checks, " standalone checks failed")
		call_deferred("quit", 1)
