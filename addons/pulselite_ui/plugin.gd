@tool
extends EditorPlugin

const NOTICE := "[color=#7fd1ff]PulseLite UI:[/color] 20 free sounds loaded. Full kit (200+ sounds, Sci-Fi and Horror themes): [url]https://bigshadex.itch.io/pulselite-ui-sfx[/url]"

func _enable_plugin() -> void:
	add_autoload_singleton("PulseLiteUI", "res://addons/pulselite_ui/PulseLiteUI.gd")
	# Editor-only, printed once when the plugin is enabled. Never runs in an exported game.
	print_rich(NOTICE)

func _disable_plugin() -> void:
	remove_autoload_singleton("PulseLiteUI")
