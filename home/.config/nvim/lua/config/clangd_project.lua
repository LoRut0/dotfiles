local M = {}

local function canonical(path)
  return vim.uv.fs_realpath(path) or vim.fs.normalize(path)
end

local function repository(path)
  return vim.fs.root(path, { ".arc", ".git" })
end

-- Only walk ancestors, never scan a monorepo or read its compilation databases.
local function database(path)
  path = canonical(path)
  local boundary = repository(path)
  if vim.fn.isdirectory(path) == 0 then
    path = vim.fs.dirname(path)
  end
  while path do
    for _, dir in ipairs({ path, path .. "/build" }) do
      if vim.fn.filereadable(dir .. "/compile_commands.json") == 1 then
        return dir
      end
    end
    if path == boundary then
      break
    end
    local parent = vim.fs.dirname(path)
    if parent == path then
      break
    end
    path = parent
  end
end

function M.resolve(bufnr)
  local name = vim.api.nvim_buf_get_name(bufnr)
  if name == "" then
    return
  end
  local file = canonical(name)
  local own = database(file)
  if own then
    return own
  end

  local repo = repository(file)
  if not repo then
    return
  end
  -- The cwd is an explicit project context, including :lcd / :tcd / :cd.
  local cwd = canonical(vim.fn.getcwd())
  if repository(cwd) == repo then
    local current = database(cwd)
    if current then
      return current
    end
  end

  -- Also support `nvim path/to/source.cpp` from the checkout root. Derive this
  -- from buffers, not live clients, so LspRestart keeps the same selection.
  local candidate
  local filetypes = { c = true, cpp = true, objc = true, objcpp = true, cuda = true }
  for _, other in ipairs(vim.api.nvim_list_bufs()) do
    if vim.api.nvim_buf_is_loaded(other) and vim.bo[other].buftype == "" and filetypes[vim.bo[other].filetype] then
      local other_name = vim.api.nvim_buf_get_name(other)
      if other_name ~= "" then
        local other_file = canonical(other_name)
        if repository(other_file) == repo then
          local found = database(other_file)
          if found then
            if candidate and candidate ~= found then
              return -- Multiple projects: use :cd to choose, never guess.
            end
            candidate = found
          end
        end
      end
    end
  end
  return candidate
end

function M.root_dir(bufnr, on_dir)
  on_dir(M.resolve(bufnr) or vim.fs.root(bufnr, vim.lsp.config.clangd.root_markers or {}))
end

function M.before_init(params, config)
  local root = config.root_dir
  if root and vim.fn.filereadable(root .. "/compile_commands.json") == 1 then
    params.initializationOptions = params.initializationOptions or {}
    -- Unlike root_dir alone, this tells clangd to use the project's database
    -- for dependency headers outside the project directory too.
    params.initializationOptions.compilationDatabasePath = root
  end
end

return M
