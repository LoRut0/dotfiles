local M = {}

-- Arc mounts and worktrees have a .arc marker, irrespective of their path.
function M.root(buf)
  local name = vim.api.nvim_buf_get_name(buf or 0)
  return M.find_root(name ~= "" and name or vim.uv.cwd())
end

function M.find_root(path)
  local root = path and vim.fs.root(path, ".arc")
  -- ~/.arc is also the global storage directory, not a checkout.
  return root and vim.uv.fs_stat(root .. "/.arc/HEAD") and root or nil
end

local function escape_regex(text)
  return (text:gsub("([\\.^$|?*+(){}%[%]])", "\\%1"))
end

local function empty()
  return function() end
end

local function remote(opts, ctx, files)
  local cwd = opts.cwd or vim.uv.cwd()
  if not M.find_root(cwd) then
    local source = files and "files" or "grep"
    return require("snacks.picker.source." .. source)[source](opts, ctx)
  end

  local search = ctx.filter.search
  if vim.trim(search) == "" then
    return empty()
  end
  if vim.fn.executable("ya") ~= 1 then
    Snacks.notify.error("Arcadia search requires `ya` on PATH")
    return empty()
  end

  -- Keep cwd scoping: remote results are relative to this checkout subtree.
  -- Limit broad queries rather than enumerating the whole monorepo.
  local args = { "grep", "--remote", "--no-colors", "-m", "1000" }
  if files then
    local pattern = escape_regex(vim.trim(search)):gsub("%s+", ".*")
    vim.list_extend(args, { "-i", "-f", pattern })
  else
    local pattern = opts.regex == false and escape_regex(search) or search
    if search == vim.fn.tolower(search) then
      args[#args + 1] = "-i"
    end
    if vim.tbl_contains(opts.args or {}, "--word-regexp") then
      args[#args + 1] = "-w"
    end
    vim.list_extend(args, { "-n", "--", pattern })
  end

  return require("snacks.picker.source.proc").proc(ctx:opts({
    cmd = "ya",
    args = args,
    cwd = cwd,
    transform = function(item)
      -- ya also prints a summary; it is not a search result.
      if item.text == "" or item.text:match("^Total:") then
        return false
      end
      item.cwd = cwd
      if files then
        item.file = item.text
      else
        local file, line, text = item.text:match("^(.-):(%d+):(.*)$")
        if not file then
          return false
        end
        item.file = file
        item.pos = { tonumber(line), 0 }
        item.line = text
      end
    end,
  }), ctx)
end

function M.grep(opts, ctx)
  return remote(opts, ctx, false)
end

function M.files(opts, ctx)
  return remote(opts, ctx, true)
end

function M.configure(opts)
  if M.find_root(opts.cwd or vim.uv.cwd()) then
    local files = opts.source == "files"
    opts.finder = files and M.files or M.grep
    opts.title = files and "Files (Arcadia trunk)" or "Grep (Arcadia trunk)"
    if files then
      -- Wait for a filename query instead of walking the Arc mount.
      opts.live = true
    end
  end
end

return M
