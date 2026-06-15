require("git"):setup({
	-- Order of status signs showing in the linemode
	order = 1500,
})

function Entity:click(event, up)
	if up then
		return -- We don't care about mouse release events
	end

	-- Hover on the file we just clicked
	ya.emit("reveal", { self._file.url })
	if event.is_middle then -- Middle click
		ya.emit("open", { interactive = true })
	elseif event.is_right then -- Right click
		ya.emit("plugin", { "smart-enter" })
	end
end
