local arcadia = require("config.arcadia")
local workspace = require("config.workspace")
local M = {}

function M.grep(remote)
  local dirs = {}
  local roots = workspace.roots()
  if #roots == 0 then
    Snacks.notify.warn("No workspace folders to search")
    return
  end
  for _, dir in ipairs(roots) do
    local root = arcadia.find_root(dir)
    if vim.fn.isdirectory(dir) == 0 then
      Snacks.notify.warn("Workspace folder is unavailable: " .. dir)
    elseif remote and not root then
      Snacks.notify.warn("Skipping workspace folder outside Arcadia: " .. dir)
    elseif not remote and dir == root then
      Snacks.notify.warn("For local search, add a workspace folder inside " .. dir .. " with :WorkspaceAdd")
    else
      dirs[#dirs + 1] = dir
    end
  end
  if #dirs == 0 then
    return
  end

  -- A parent search already includes any nested workspace folders.
  dirs = vim.tbl_filter(function(dir)
    return not vim.iter(dirs):any(function(parent)
      return parent ~= dir and vim.fs.relpath(parent, dir) ~= nil
    end)
  end, dirs)

  if not remote then
    return Snacks.picker.grep({
      title = "Grep Workspace (local)",
      dirs = dirs,
      finder = require("snacks.picker.source.grep").grep,
    })
  end

  local finders = vim.tbl_map(function(dir)
    return function(opts, ctx)
      local scoped = vim.tbl_extend("force", opts, { cwd = dir })
      return arcadia.grep(scoped, ctx:clone(scoped))
    end
  end, dirs)
  return Snacks.picker.grep({ title = "Grep Workspace (Arcadia trunk)", finder = finders })
end

function M.arcadia_folder()
  local root = arcadia.root() or arcadia.find_root(vim.fn.getcwd(0))
  if not root then
    for _, dir in ipairs(workspace.roots()) do
      root = arcadia.find_root(dir)
      if root then
        break
      end
    end
  end
  if not root then
    Snacks.notify.warn("Open an Arcadia file or workspace folder to search trunk")
    return
  end
  root = vim.uv.fs_realpath(root) or root
  Snacks.input({ prompt = "Arcadia folder", default = root .. "/", completion = "dir" }, function(value)
    if not value then
      return
    end
    local dir = require("config.workspace_file").path(value == "" and "." or value, root)
    if not vim.fs.relpath(root, dir) or vim.fn.isdirectory(dir) == 0 then
      Snacks.notify.warn("Choose a directory inside " .. root)
      return
    end
    Snacks.picker.grep({ cwd = dir })
  end)
end

return M
