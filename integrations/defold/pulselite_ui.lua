-- PulseLite UI SFX: minimal Defold helper (first draft, AI-assisted, MIT).
-- Not yet tested inside Defold. Feedback and fixes welcome:
-- https://github.com/BigShadex/pulselite-ui-godot
--
-- Setup:
-- 1. Copy the OGG (or WAV) files into your project, e.g. /sounds/click/click_03.ogg
-- 2. Make one game object (e.g. "ui_sfx") and add a Sound component per file you use.
--    Name each component after the file without extension, e.g. "click_03".
-- 3. In a script: local sfx = require "pulselite_ui"
--                 sfx.init("/ui_sfx")            -- path or url of that game object
--                 sfx.play("button_click")       -- event names below
--
-- Levels are already balanced between events, so every event starts at gain 1.0.

local M = {}

-- event -> recommended file, alternates, suggested pitch jitter (+/-)
-- Mirrors addons/pulselite_ui/ui_events.json (free sample files).
M.events = {
	button_click = { "click_03", { "click_09" }, 0.03 },
	button_hover = { "hover_01", { "hover_05" }, 0.03 },
	toggle_on    = { "toggle_01", {}, 0.03 },
	toggle_off   = { "toggle_02", {}, 0.03 },
	menu_confirm = { "confirm_05", { "confirm_06" }, 0.03 },
	menu_back    = { "back_cancel_01", {}, 0.03 },
	error        = { "error_01", { "error_03" }, 0.03 },
	notification = { "notify_02", { "notify_05" }, 0.0 },
	panel_open   = { "panel_open_04", {}, 0.03 },
	panel_close  = { "panel_close_05", {}, 0.03 },
	transition   = { "whoosh_06", {}, 0.03 },
	coin_pickup  = { "coin_01", { "coin_07" }, 0.03 },
	reward       = { "reward_05", {}, 0.0 },
	level_up     = { "level_up_01", {}, 0.0 },
}

M.gain = 1.0          -- master UI volume
M.use_alternates = true

local base = nil

-- go_path: the game object holding the sound components, e.g. "/ui_sfx" or "main:/ui_sfx"
function M.init(go_path)
	base = go_path
	math.randomseed(os.time())
end

local function pick(entry)
	local files = { entry[1] }
	if M.use_alternates then
		for _, f in ipairs(entry[2]) do files[#files + 1] = f end
	end
	return files[math.random(#files)]
end

-- Play a UI event. opts (optional): { gain = 0.8 }
function M.play(event, opts)
	local entry = M.events[event]
	if not entry then
		print("pulselite_ui: unknown event " .. tostring(event))
		return
	end
	assert(base, "pulselite_ui: call init(go_path) first")
	local jitter = entry[3]
	local speed = 1.0
	if jitter > 0 then speed = 1.0 + (math.random() * 2 - 1) * jitter end
	local gain = M.gain * ((opts and opts.gain) or 1.0)
	sound.play(msg.url(nil, base, pick(entry)), { gain = gain, speed = speed })
end

-- Convenience for toggles: sfx.toggle(is_on)
function M.toggle(is_on)
	M.play(is_on and "toggle_on" or "toggle_off")
end

return M
