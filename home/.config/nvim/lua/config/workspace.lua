local file = require("config.workspace_file")
local M = {}
local active
local next_id = 0

local function refresh_views()
  for _, picker in ipairs(Snacks.picker.get({ source = "explorer", tab = false })) do
    if picker.opts.workspace_id then
      if active and picker.opts.workspace_id == active.id then
        picker.title = active.path and vim.fs.basename(active.path) or "Workspace"
        picker:refresh()
      else
        picker:close()
      end
    end
  end
end

local function activate(path, folders)
  next_id = next_id + 1
  active = { id = next_id, path = path, folders = folders, collapsed = {} }
  refresh_views()
end

local function find_folder(folders, path)
  for i, folder in ipairs(folders) do
    if folder.path == path then
      return i
    end
  end
end

local function load_folders(path)
  local doc = file.load(path)
  local seen = {}
  doc.folders = vim.tbl_filter(function(folder)
    if not seen[folder.path] then
      seen[folder.path] = true
      return true
    end
    return false
  end, doc.folders)
  return doc
end

local function open(path)
  path = file.path(path)
  activate(path, load_folders(path).folders)
end

local function add(path)
  path = file.path(path)
  assert(vim.fn.isdirectory(path) == 1, "Not a directory: " .. path)
  if not active then
    activate(nil, { { path = path } })
    return
  end
  local doc = active.path and load_folders(active.path)
  local folders = doc and doc.folders or active.folders
  if not find_folder(folders, path) then
    if doc then
      file.add(doc, path)
    end
    folders[#folders + 1] = { path = path }
  end
  active.folders = folders
  refresh_views()
end

local function remove(path)
  assert(active, "Open a workspace or add a folder first")
  path = file.path(path)
  local doc = active.path and load_folders(active.path)
  local folders = doc and doc.folders or active.folders
  local index = find_folder(folders, path)
  assert(index, "Folder is not in the workspace: " .. path)
  if doc then
    file.remove(doc, path)
  end
  table.remove(folders, index)
  active.folders = folders
  active.collapsed[path] = nil
  refresh_views()
end

local function save(path)
  assert(active, "Open a workspace or add a folder first")
  assert(not active.path, "This workspace is already saved at " .. tostring(active.path))
  path = file.path(path)
  if not vim.endswith(path, ".code-workspace") then
    path = path .. ".code-workspace"
  end
  file.save(path, active.folders)
  active.path = path
  refresh_views()
end

local function checked(action, value)
  if not value or value == "" then
    return
  end
  local ok, err = pcall(action, value)
  if not ok then
    vim.notify(tostring(err):gsub("^.-%.lua:%d+: ", ""), vim.log.levels.ERROR)
  end
end

local function input_command(name, action, prompt, completion)
  vim.api.nvim_create_user_command(name, function(opts)
    if opts.args ~= "" then
      checked(action, opts.args:gsub("\\([ \t])", "%1"))
    else
      Snacks.input({ prompt = prompt, completion = completion }, function(value)
        checked(action, value)
      end)
    end
  end, { nargs = "?", complete = completion, desc = prompt })
end

function M.setup()
  input_command("WorkspaceOpen", open, "Open workspace", "file")
  input_command("WorkspaceAdd", add, "Add folder to workspace", "dir")
  input_command("WorkspaceSave", save, "Save workspace", "file")
  vim.api.nvim_create_user_command("WorkspaceRemove", function(opts)
    if opts.args ~= "" then
      checked(remove, opts.args:gsub("\\([ \t])", "%1"))
    elseif active then
      vim.ui.select(active.folders, {
        prompt = "Remove folder from workspace",
        format_item = function(folder)
          return folder.name and (folder.name .. "  " .. folder.path) or folder.path
        end,
      }, function(folder)
        checked(remove, folder and folder.path)
      end)
    end
  end, {
    nargs = "?",
    desc = "Remove folder from workspace",
    complete = function(prefix)
      return vim
        .iter(active and active.folders or {})
        :map(function(folder)
          return folder.path
        end)
        :filter(function(path)
          return vim.startswith(path, prefix)
        end)
        :totable()
    end,
  })
  vim.api.nvim_create_user_command("WorkspaceClose", function()
    active = nil
    refresh_views()
  end, { desc = "Close workspace" })
end

function M.explore(project)
  local view = project and "project" or (active and "workspace" or "cwd")
  local current = Snacks.picker.get({ source = "explorer" })[1]
  if current then
    local previous = current.opts.explorer_view or "cwd"
    current:close()
    if view == previous then
      return
    end
  end
  local opts = {}
  if project then
    opts.cwd = LazyVim.root()
  elseif active then
    if active.path then
      checked(function(path)
        active.folders = load_folders(path).folders
        refresh_views()
      end, active.path)
    end
    opts = require("config.workspace_explorer").options(active)
  end
  opts.explorer_view = view
  return Snacks.explorer(opts)
end

return M
