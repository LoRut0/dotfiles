local function searching(picker)
  return picker.input.filter.meta.searching
end

local function collapsed(picker)
  picker._collapsed_search_dirs = picker._collapsed_search_dirs or {}
  return picker._collapsed_search_dirs
end

local function toggle_directory(picker, item)
  local dirs = collapsed(picker)
  dirs[item.file] = not dirs[item.file] or nil
  picker.list:set_target()
  picker:find()
end

return {
  "folke/snacks.nvim",
  keys = {
    { "<leader>e", function() Snacks.explorer() end, desc = "Explorer (cwd)" },
    { "<leader>E", function() Snacks.explorer({ cwd = LazyVim.root() }) end, desc = "Explorer (Root Dir)" },
  },
  opts = {
    picker = {
      sources = {
        explorer = {
          hidden = true,
          ignored = {},
          -- Following an opened file would clear the active explorer search.
          follow_file = false,
          transform = function(item, ctx)
            if ctx.filter:is_empty() then
              return
            end
            for dir in pairs(collapsed(ctx.picker)) do
              if item.file:sub(1, #dir + 1) == dir .. "/" then
                return false
              end
              if item.file == dir then
                item.open = false
              end
            end
          end,
          actions = {
            apply_filter = function(picker)
              picker:focus("list")
            end,
            clear_filter = function(picker)
              if picker.input:get() ~= "" then
                picker._collapsed_search_dirs = nil
                picker.input:set("", "")
                picker:find()
              else
                picker:focus("list")
              end
            end,
            confirm_filtered = function(picker, item, action)
              if not searching(picker) then
                return require("snacks.explorer.actions").actions.confirm(picker, item, action)
              end
              if not item then
                return
              end
              if item.dir then
                toggle_directory(picker, item)
              else
                Snacks.picker.actions.jump(picker, item, action)
              end
            end,
            close_filtered = function(picker, item)
              if not searching(picker) then
                return require("snacks.explorer.actions").actions.explorer_close(picker, item)
              end
              local dir = item and (item.dir and item.file or item.parent and item.parent.file)
              if dir and not collapsed(picker)[dir] then
                toggle_directory(picker, { file = dir })
              end
            end,
          },
          win = {
            input = {
              keys = {
                ["<CR>"] = { "apply_filter", mode = { "i", "n" } },
                ["<Esc>"] = { "clear_filter", mode = { "i", "n" } },
              },
            },
            list = {
              keys = {
                ["<CR>"] = "confirm_filtered",
                ["l"] = "confirm_filtered",
                ["h"] = "close_filtered",
              },
            },
          },
        },
      },
    },
  },
}
