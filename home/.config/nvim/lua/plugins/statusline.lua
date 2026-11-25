local function directory()
  if vim.bo.filetype:match("^snacks_picker_") then
    for _, picker in ipairs(Snacks.picker.get({ source = "explorer" })) do
      if picker:is_focused() then
        local item = picker:current({ resolve = false })
        return (item and item.workspace_root) or picker:cwd()
      end
    end
  end
  local term = vim.b.snacks_terminal
  if term and term.cwd then
    return term.cwd
  end
  local file = vim.api.nvim_buf_get_name(0)
  return vim.bo.buftype == "" and file ~= "" and vim.fs.dirname(file) or vim.fn.getcwd(0)
end

local function read_branch(root, vcs, done)
  local function run(cmd, callback)
    local ok = pcall(vim.system, cmd, { cwd = root, text = true, timeout = 5000 }, vim.schedule_wrap(callback))
    if not ok then
      done("")
    end
  end
  if vcs == "arc" then
    run({ "arc", "info", "--json" }, function(result)
      local ok, info = pcall(vim.json.decode, result.stdout or "")
      if result.code ~= 0 or not ok or type(info) ~= "table" then
        return done("")
      end
      if type(info.branch) == "string" and info.branch ~= "" then
        return done(info.branch)
      end
      done(type(info.hash) == "string" and info.hash:sub(1, 8) or "")
    end)
  else
    run({ "git", "symbolic-ref", "--quiet", "--short", "HEAD" }, function(result)
      if result.code == 1 then -- detached HEAD
        return run({ "git", "rev-parse", "--short", "HEAD" }, function(head)
          done(head.code == 0 and vim.trim(head.stdout) or "")
        end)
      end
      done(result.code == 0 and vim.trim(result.stdout) or "")
    end)
  end
end

local function checkout(dir)
  local root = require("config.arcadia").find_root(dir)
  if root then
    return "arc", root, root .. "/.arc/HEAD"
  end
  -- Lualine resolves Git's metadata directory for linked worktrees and submodules.
  local git_dir = require("lualine.components.branch.git_branch").find_git_dir(dir)
  if git_dir then
    local tables = git_dir .. "/reftable/tables.list"
    return "git", git_dir, vim.uv.fs_stat(tables) and tables or git_dir .. "/HEAD"
  end
end

return {
  "nvim-lualine/lualine.nvim",
  opts = function(_, opts)
    local last_dir, head, request
    local name = ""
    local watch = assert(vim.uv.new_fs_poll())

    local function update(force)
      local dir = directory()
      if dir == last_dir and not force then
        return
      end
      last_dir = dir
      local vcs, root, file = checkout(dir)
      if head ~= file then
        name = ""
      elseif not force then
        return
      end
      watch:stop()
      head, request = file, nil
      if not file then
        return
      end

      local function refresh()
        if head ~= file then
          return
        end
        local token = {}
        request = token
        read_branch(root, vcs, function(value)
          if request == token and name ~= value then
            name = value
            require("lualine").refresh()
          end
        end)
      end
      watch:start(file, 1000, vim.schedule_wrap(refresh))
      refresh()
    end

    vim.api.nvim_create_autocmd({ "FocusGained", "ShellCmdPost" }, {
      group = vim.api.nvim_create_augroup("StatuslineBranch", { clear = true }),
      callback = function()
        update(true)
      end,
    })

    local function branch()
      update(false)
      return require("lualine.utils.utils").stl_escape(name)
    end

    opts.sections.lualine_b[1] = { branch, icon = "" }
  end,
}
