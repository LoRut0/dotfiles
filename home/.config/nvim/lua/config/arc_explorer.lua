local M = {}

local codes = { modified = "M", typechange = "T", ["new file"] = "A", deleted = "D", renamed = "R", copied = "C" }

local function tree_status(root, groups)
  local paths = {}
  for _, entry in ipairs(groups.staged or {}) do
    paths[entry.path] = (codes[entry.status] or "M") .. " "
  end
  for _, entry in ipairs(groups.changed or {}) do
    local staged = (paths[entry.path] or " "):sub(1, 1)
    paths[entry.path] = staged .. (codes[entry.status] or "M")
  end
  for _, entry in ipairs(groups.untracked or {}) do
    paths[entry.path] = "??"
  end
  for _, entry in ipairs(groups.unmerged or {}) do
    paths[entry.path] = "UU"
  end

  local entries = {}
  for path, status in pairs(paths) do
    entries[#entries + 1] = { file = root .. "/" .. path, status = status }
  end
  return entries
end

function M.finder(opts, ctx, collapsed)
  local cwd = ctx.filter.cwd
  local root = opts.git_status and require("config.arcadia").find_root(cwd)
  local find
  if collapsed then
    find = function(cb)
      local status = root and require("snacks.explorer.tree"):find(cwd).status or nil
      cb({ text = cwd, file = cwd, dir = true, open = false, status = status })
    end
  else
    local tree_opts = root and vim.tbl_extend("force", opts, { git_status = false }) or opts
    find = require("snacks.picker.source.explorer").explorer(tree_opts, ctx)
  end
  if not root or vim.fn.executable("arc") ~= 1 then
    return find
  end

  -- Use the picker's async process so closing or replacing a search cancels it.
  local read = require("snacks.picker.source.proc").proc({
    cmd = "arc",
    args = { "status", "--json", "-u", opts.git_untracked and "all" or "no", "--", "." },
    cwd = cwd,
    raw = true,
    notify = false,
  }, ctx)
  return function(cb)
    local chunks = {}
    read(function(chunk)
      chunks[#chunks + 1] = chunk.text
    end)
    local ok, result = pcall(vim.json.decode, table.concat(chunks))
    local entries = ok and tree_status(root, result.status or {}) or {}
    -- Feed the same tree used by Snacks for icons, parent folders and ]g / [g.
    require("snacks.explorer.git")._update(cwd, entries)
    find(cb)
  end
end

return M
