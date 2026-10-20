extends SceneTree
## Native controller/resource/signal checks; no claim about audible quality or visual input.

const PRESET = "res://addons/pulselite_ui/integrations/maaack/PulseLiteFree.tscn"
const SOUNDS = "res://addons/pulselite_ui/sounds/"
const HOVER = "hover/hover_01.wav"
const CLICK = "click/click_03.wav"
const TYPE = "click/click_09.wav"
const CONFIRM = "confirm/confirm_05.wav"
const ERROR = "error/error_01.wav"
const EXPECTED = {
	"button_hovered": HOVER, "button_focused": HOVER, "button_pressed": CLICK,
	"tab_hovered": HOVER, "tab_changed": CLICK,
	"slider_hovered": HOVER, "slider_focused": HOVER,
	"slider_drag_started": CLICK, "slider_drag_ended": CONFIRM,
	"line_hovered": HOVER, "line_focused": HOVER, "line_text_changed": TYPE,
	"line_text_submitted": CONFIRM, "line_text_change_rejected": ERROR,
	"item_list_selected": CLICK, "item_list_activated": CONFIRM,
	"tree_item_selected": CLICK, "tree_item_activated": CONFIRM, "tree_button_clicked": CLICK,
}
var failures: Array[String] = []
var checks: int = 0


func _initialize() -> void:
	call_deferred("_run")


func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)
		printerr("FAIL: ", message)


func stop_players(controller: Node) -> void:
	for child in controller.get_children():
		if child is AudioStreamPlayer:
			child.stop()


func signal_plays(controller: Node, control: Node, signal_name: String, property: String, arguments: Array = []) -> void:
	stop_players(controller)
	control.callv("emit_signal", [signal_name] + arguments)
	var player = controller.get(property + "_player")
	check(player != null and player.playing, property + " starts its actual AudioStreamPlayer")
	var playing: int = 0
	for child in controller.get_children():
		if child is AudioStreamPlayer and child.playing:
			playing += 1
	check(playing == 1, property + " starts exactly one player")


func _run() -> void:
	var scene = load(PRESET)
	check(scene is PackedScene, "preset is a native PackedScene")
	if not scene is PackedScene:
		finish()
		return
	var ui = Control.new()
	root.add_child(ui)
	var button = Button.new()
	var tab = TabBar.new()
	tab.add_tab("One")
	var slider = HSlider.new()
	var line = LineEdit.new()
	var items = ItemList.new()
	items.add_item("One")
	var tree = Tree.new()
	var tree_item = tree.create_item()
	for control in [button, tab, slider, line, items, tree]:
		ui.add_child(control)
	var controller = scene.instantiate()
	ui.add_child(controller)
	await process_frame
	check(controller.get_script().resource_path == "res://addons/maaacks_ui_sound_controller/base/scripts/ui_sound_controller.gd", "real upstream script is attached")
	check(controller.get("root_node") == ui, "preset scans its parent")
	check(controller.get("audio_bus") == &"Master", "default bus exists without enabling another plugin")
	check(controller.process_mode == Node.PROCESS_MODE_ALWAYS, "preset handles paused menus")
	check(controller.get("persistent"), "late controls are supported")
	for property in EXPECTED:
		var stream = controller.get(property)
		check(stream is AudioStream, property + " resolves to an AudioStream")
		if stream is AudioStream:
			check(stream.resource_path == SOUNDS + EXPECTED[property], property + " uses the specified free file")
		var player = controller.get(property + "_player")
		check(player is AudioStreamPlayer and player.stream == stream, property + " creates the upstream player")
	check(controller.get("tab_selected") == null and controller.get("tab_selected_player") == null,
		"tab_selected stays silent to avoid doubling tab_changed")

	signal_plays(controller, button, "mouse_entered", "button_hovered")
	signal_plays(controller, button, "focus_entered", "button_focused")
	signal_plays(controller, button, "pressed", "button_pressed")
	signal_plays(controller, tab, "tab_hovered", "tab_hovered", [0])
	signal_plays(controller, tab, "tab_changed", "tab_changed", [0])
	stop_players(controller)
	tab.emit_signal("tab_selected", 0)
	check(not controller.get("tab_changed_player").playing, "tab_selected does not replay tab_changed")
	signal_plays(controller, slider, "mouse_entered", "slider_hovered")
	signal_plays(controller, slider, "focus_entered", "slider_focused")
	signal_plays(controller, slider, "drag_started", "slider_drag_started")
	signal_plays(controller, slider, "drag_ended", "slider_drag_ended", [true])
	signal_plays(controller, line, "mouse_entered", "line_hovered")
	signal_plays(controller, line, "focus_entered", "line_focused")
	signal_plays(controller, line, "text_changed", "line_text_changed", ["typed"])
	signal_plays(controller, line, "text_submitted", "line_text_submitted", ["submitted"])
	signal_plays(controller, line, "text_change_rejected", "line_text_change_rejected", ["rejected"])
	signal_plays(controller, items, "item_selected", "item_list_selected", [0])
	signal_plays(controller, items, "item_activated", "item_list_activated", [0])
	signal_plays(controller, tree, "item_selected", "tree_item_selected")
	signal_plays(controller, tree, "item_activated", "tree_item_activated")
	signal_plays(controller, tree, "button_clicked", "tree_button_clicked", [tree_item, 0, 0, 1])

	controller.connect_ui_sounds(button)
	controller.connect_ui_sounds(button)
	check(button.get_signal_connection_list("pressed").size() == 1, "repeat scans keep one press connection")
	var late_button = Button.new()
	ui.add_child(late_button)
	await process_frame
	signal_plays(controller, late_button, "pressed", "button_pressed")
	paused = true
	signal_plays(controller, button, "pressed", "button_pressed")
	paused = false
	stop_players(controller)
	await create_timer(0.1).timeout
	# Check cleanup after an actual free, independent of version-specific frame order.
	controller.free()
	check(button.get_signal_connection_list("pressed").is_empty(), "freeing the preset disconnects the controller")
	var after_free = Button.new()
	ui.add_child(after_free)
	check(after_free.get_signal_connection_list("pressed").is_empty(), "no persistent wiring remains after free")
	ui.queue_free()
	await process_frame
	finish()


func finish() -> void:
	if failures.is_empty():
		print("PASS Maaack integration: ", checks, " native assertions")
		call_deferred("quit", 0)
	else:
		printerr(failures.size(), " / ", checks, " checks failed")
		call_deferred("quit", 1)
