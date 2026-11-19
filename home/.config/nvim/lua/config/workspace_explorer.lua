local M = {}

local function refresh(picker, on_done)
  picker.list:set_target()
  picker:find({ on_done = on_done })
end

local function watch_directories()
  local uv = vim.uv
  local watches, dirty = {}, {}
  local pending = false
  local function changed(picker, path)
    dirty[path] = true
    if pending then
      return
    end
    pending = true
    vim.defer_fn(function()
      pending = false
      if picker.closed then
        return
      end
      local tree = require("snacks.explorer.tree")
      for dir in pairs(dirty) do
        tree:refresh(dir)
      end
      dirty = {}
      refresh(picker)
    end, 100)
  end
  local function sync(picker, paths, keep_old)
    if not keep_old then
      for path, handle in pairs(watches) do
        if not paths[path] then
          handle:close()
          watches[path] = nil
        end
      end
    end
    for path in pairs(paths) do
      if not watches[path] then
        local handle = assert(uv.new_fs_event())
        local initial = uv.fs_stat(path)
        local ok = handle:start(path, {}, function()
          changed(picker, path)
        end)
        if ok then
          watches[path] = handle
          -- FSEvents can miss changes before a newly registered watch is ready.
          vim.defer_fn(function()
            if watches[path] == handle and initial then
              local stat = uv.fs_stat(path)
              if not stat or not vim.deep_equal(stat.mtime, initial.mtime) then
                changed(picker, path)
              end
            end
          end, 250)
        else
          handle:close()
        end
      end
    end
  end
  return sync
end

function M.options(workspace)
  local tree = require("snacks.explorer.tree")
  local explorer = require("snacks.picker.source.explorer")
  local sync_watches = watch_directories()
  local generation = 0
  local first = vim.iter(workspace.folders):find(function(root)
    return vim.fn.isdirectory(root.path) == 1
  end)

  local function finder(opts, ctx)
    generation = generation + 1
    local current_generation = generation
    local search = not ctx.filter:is_empty()
    if #workspace.folders == 0 then
      sync_watches(ctx.picker, {})
      return {}
    end
    local finders, watched = {}, {}
    for i, root in ipairs(workspace.folders) do
      local exists = vim.fn.isdirectory(root.path) == 1
      local find
      if exists then
        watched[root.path] = true
      end
      if exists and (search or not workspace.collapsed[root.path]) then
        local scoped = ctx:clone()
        scoped.filter = ctx.filter:clone()
        scoped.filter:set_cwd(root.path)
        find = explorer.explorer(opts, scoped)
      end
      finders[i] = { root = root, find = find, exists = exists }
    end
    sync_watches(ctx.picker, watched, true)
    return function(cb)
      for i, entry in ipairs(finders) do
        if current_generation ~= generation or ctx.picker.closed then
          return
        end
        local root = entry.root
        local prefix = ("%08d/"):format(i)
        local top = entry.find and not search and tree:find(root.path) or nil
        local was_open = top and top.open
        local function add(item)
          if top and item.file == root.path and not item.parent then
            -- Snacks opens its cwd when enumerating it. Keep the node's state
            -- for cases where it also appears inside another selected root.
            top.open = was_open
          end
          if current_generation ~= generation or ctx.picker.closed then
            return
          end
          item.workspace_root = root.path
          item.sort = prefix .. (item.sort or "")
          if not item.parent and item.file == root.path then
            item.workspace_top = true
            item.workspace_name = root.name
          end
          if not search and item.dir and item.open then
            watched[item.file] = true
          end
          cb(item)
        end
        if entry.find then
          entry.find(add)
        elseif not search then
          add({
            file = root.path,
            text = root.path,
            dir = true,
            open = false,
            comment = not entry.exists and "[unavailable]" or nil,
          })
        end
      end
      if not search and not ctx.picker.closed and generation == current_generation then
        sync_watches(ctx.picker, watched)
      end
    end
  end

  local function for_root(action)
    return function(picker, item, ...)
      if item and item.workspace_root then
        if vim.fn.isdirectory(item.workspace_root) == 0 then
          vim.notify("Workspace folder is unavailable: " .. item.workspace_root, vim.log.levels.WARN)
          return
        end
        picker:set_cwd(item.workspace_root)
      elseif not item then
        return
      end
      return explorer.actions[action](picker, item, ...)
    end
  end

  local function guard_roots(action)
    local run = for_root(action)
    return function(picker, item, ...)
      local selected = picker:selected({ fallback = true })
      if action == "explorer_rename" then
        selected = item and { item } or {}
      end
      for _, candidate in ipairs(selected) do
        if vim.iter(workspace.folders):any(function(root)
          return root.path == candidate.file
        end) then
          vim.notify("Use :WorkspaceRemove to remove a folder from the workspace", vim.log.levels.WARN)
          return
        end
      end
      return run(picker, item, ...)
    end
  end

  return {
    workspace_id = workspace.id,
    cwd = first and first.path or vim.fn.getcwd(),
    title = workspace.path and vim.fs.basename(workspace.path) or "Workspace",
    show_empty = true,
    finder = finder,
    watch = false, -- stock Explorer only watches its own picker cwd
    on_close = function(picker)
      sync_watches(picker, {})
      -- Reopening a workspace uses its current folders instead of a picker snapshot.
      vim.schedule(function()
        local resume = require("snacks.picker.resume").state
        if resume.explorer and resume.explorer.opts == picker.init_opts then
          resume.explorer = nil
        end
      end)
    end,
    format = function(item, picker)
      local result = Snacks.picker.format.file(item, picker)
      if item.workspace_name then
        for _, part in ipairs(result) do
          if part.field == "file" then
            part[1] = item.workspace_name
            break
          end
        end
      end
      return result
    end,
    actions = {
      workspace_fold_root = function(picker, item, closed, on_done)
        workspace.collapsed[item.file] = closed or nil
        refresh(picker, on_done)
      end,
      explorer_update = function(picker)
        for _, root in ipairs(workspace.folders) do
          tree:refresh(root.path)
        end
        refresh(picker)
      end,
      explorer_close_all = function(picker)
        for _, root in ipairs(workspace.folders) do
          workspace.collapsed[root.path] = true
          tree:close_all(root.path)
        end
        refresh(picker)
      end,
      explorer_up = function(picker, item)
        if item and item.parent then
          for candidate, index in picker:iter() do
            if candidate == item.parent then
              picker.list:view(index)
              return
            end
          end
        end
      end,
      explorer_add = for_root("explorer_add"),
      explorer_focus = for_root("explorer_focus"),
      explorer_copy = for_root("explorer_copy"),
      explorer_paste = for_root("explorer_paste"),
      explorer_rename = guard_roots("explorer_rename"),
      explorer_del = guard_roots("explorer_del"),
      explorer_move = guard_roots("explorer_move"),
      explorer_git_next = for_root("explorer_git_next"),
      explorer_git_prev = for_root("explorer_git_prev"),
      explorer_diagnostic = for_root("explorer_diagnostic"),
    },
  }
end

return M
