extends Control
## Tiny PulseLite UI demo: every button and toggle below is wired with one call.

const EVENT_BUTTONS := ["menu_confirm", "menu_back", "error", "notification", "panel_open",
	"panel_close", "transition", "coin_pickup", "reward", "level_up"]

@onready var grid: GridContainer = %EventGrid


func _ready() -> void:
	for e in EVENT_BUTTONS:
		var b := Button.new()
		b.text = e
		b.custom_minimum_size = Vector2(220, 52)
		b.set_meta("pulselite_event", e)  # plays this event instead of button_click
		grid.add_child(b)
	PulseLiteUI.wire_buttons(self)
