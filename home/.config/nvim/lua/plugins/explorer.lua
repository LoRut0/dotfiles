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

local function clear_filter(picker, item)
  item = item or picker._explorer_filter_origin
  local row = picker.list.cursor - picker.list.top
  picker:norm(function()
    if picker.closed then
      return
    end
    picker._explorer_filter_origin = nil
    picker._collapsed_search_dirs = nil
    local filter = picker.input.filter
    local had_filter = not filter:is_empty() or searching(picker)
    if picker.input.win:valid() then
      picker.input:set("", "")
    else
      filter.pattern, filter.search = "", ""
    end
    picker:toggle("input", { enable = false, focus = "list" })
    if not had_filter then
      return
    end

    local function restore_cursor()
      if not item or picker.closed or not filter:is_empty() then
        return
      end
      for candidate, index in picker:iter() do
        if candidate.file == item.file and candidate.workspace_root == item.workspace_root then
          picker.list:set_target(index, math.max(1, index - row), { force = true })
          picker.list:render()
          return
        end
      end
    end
    if item and item.parent then
      require("snacks.explorer.tree"):show(item.file)
      if item.workspace_root then
        return picker.opts.actions.workspace_fold_root(picker, { file = item.workspace_root }, false, restore_cursor)
      end
    end
    picker:find({ on_done = restore_cursor })
  end)
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
            open_filter = function(picker, item)
              if picker.input.filter:is_empty() then
                picker._explorer_filter_origin = item
              end
              Snacks.picker.actions.focus_input(picker)
            end,
            apply_filter = function(picker)
              picker:focus("list")
            end,
            clear_filter = clear_filter,
            cancel_filter = function(picker, item)
              if not picker.input.filter:is_empty() or searching(picker) then
                return clear_filter(picker, item)
              end
              Snacks.picker.actions.cancel(picker)
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
                ["/"] = "open_filter",
                ["i"] = "open_filter",
                ["<Esc>"] = "cancel_filter",
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
