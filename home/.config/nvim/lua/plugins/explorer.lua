local function searching(picker)
  return picker.input.filter.meta.searching
end

local function collapsed(picker, item)
  picker._collapsed_search_dirs = picker._collapsed_search_dirs or {}
  local root = item.workspace_root or false
  picker._collapsed_search_dirs[root] = picker._collapsed_search_dirs[root] or {}
  return picker._collapsed_search_dirs[root]
end

local function toggle_directory(picker, item)
  local dirs = collapsed(picker, item)
  dirs[item.file] = not dirs[item.file] or nil
  picker.list:set_target()
  picker:find()
end

return {
  "folke/snacks.nvim",
  init = function()
    if not vim.g.vscode then
      require("config.workspace").setup()
    end
  end,
  keys = {
    {
      "<leader>e",
      function()
        require("config.workspace").explore()
      end,
      desc = "Explorer (Workspace or cwd)",
    },
    {
      "<leader>E",
      function()
        require("config.workspace").explore(true)
      end,
      desc = "Explorer (Root Dir)",
    },
  },
  opts = {
    picker = {
      sources = {
        explorer = {
          hidden = false,
          ignored = {},
          -- Following an opened file would clear the active explorer search.
          follow_file = false,
          transform = function(item, ctx)
            if ctx.filter:is_empty() then
              return
            end
            for dir in pairs(collapsed(ctx.picker, item)) do
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
                if item and item.workspace_top then
                  return picker.opts.actions.workspace_fold_root(picker, item, item.open)
                end
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
                if item and item.workspace_root then
                  local dir = (item.workspace_top or (item.dir and item.open)) and item or item.parent
                  if dir and dir.workspace_top then
                    return picker.opts.actions.workspace_fold_root(picker, dir, true)
                  end
                  picker:set_cwd(item.workspace_root)
                end
                return require("snacks.explorer.actions").actions.explorer_close(picker, item)
              end
              local dir = item and (item.dir and item or item.parent)
              if dir and not collapsed(picker, dir)[dir.file] then
                toggle_directory(picker, dir)
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
