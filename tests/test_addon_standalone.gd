extends SceneTree


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var script = load("res://addons/pulselite_ui/PulseLiteUI.gd")
	if script == null:
		quit(1)
		return
	var player = script.new()
	root.add_child(player)
	var voice = player.play(&"button_click")
	if voice == null or voice.stream == null or not voice.playing:
		push_error("Standalone PulseLite playback failed without Maaack installed")
		quit(1)
		return
	player.stop_all()
	# Let the audio thread consume the stop before tearing down its WAV resource.
	await create_timer(0.1).timeout
	voice = null
	player.free()
	script = null
	print("PASS standalone: existing addon loads and plays without Maaack")
	call_deferred("quit", 0)
