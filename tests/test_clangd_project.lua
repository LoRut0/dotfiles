-- Run from the dotfiles root: nvim --headless -u NONE -l tests/test_clangd_project.lua
-- Uses temporary fixtures only; does not run clangd, ya, or a service build.
package.path = vim.fn.getcwd() .. "/home/.config/nvim/lua/?.lua;" .. package.path
local project = require("config.clangd_project")
local original_cwd = vim.fn.getcwd()
local temp = vim.fn.tempname()
vim.fn.mkdir(temp, "p")
temp = assert(vim.uv.fs_realpath(temp))

local function write(path, contents)
  vim.fn.mkdir(vim.fs.dirname(path), "p")
  vim.fn.writefile({ contents or "" }, path)
end

local function buffer(path)
  write(path)
  local buf = vim.fn.bufadd(path)
  vim.fn.bufload(buf)
  vim.bo[buf].filetype = "cpp"
  return buf
end

local checks = 0
local function equal(expected, actual, message)
  assert(expected == actual, message .. ": expected " .. tostring(expected) .. ", got " .. tostring(actual))
  checks = checks + 1
end

local ok, err = xpcall(function()
  local repo = temp .. "/arcadia"
  local service = repo .. "/services/one"
  local second = repo .. "/services/two"
  vim.fn.mkdir(repo .. "/.arc", "p")
  write(service .. "/compile_commands.json", "[]")
  write(second .. "/compile_commands.json", "[]")
  local header = buffer(repo .. "/libraries/shared/include/shared.hpp")
  vim.fn.chdir(service)
  equal(service, project.resolve(header), "dependency header uses cwd database")

  local source = buffer(service .. "/src/main.cpp")
  vim.fn.chdir(repo)
  equal(service, project.resolve(header), "header uses the sole open project without an LSP client")
  local other_source = buffer(second .. "/src/main.cpp")
  equal(nil, project.resolve(header), "ambiguous open projects are not guessed")
  vim.fn.chdir(service)
  equal(service, project.resolve(header), "cwd resolves ambiguity")
  equal(second, project.resolve(other_source), "a different source keeps its own database")
  vim.fn.chdir(second)
  equal(second, project.resolve(header), "changing cwd selects another context")

  local other_repo = temp .. "/other-checkout"
  vim.fn.mkdir(other_repo .. "/.arc", "p")
  local foreign_header = buffer(other_repo .. "/libraries/shared.hpp")
  equal(nil, project.resolve(foreign_header), "no database borrowed from another checkout")
  write(temp .. "/compile_commands.json", "[]")
  equal(nil, project.resolve(foreign_header), "ancestor search stops at checkout boundary")

  local git_repo = temp .. "/git-project"
  write(git_repo .. "/.git", "gitdir: /example/worktree")
  write(git_repo .. "/build/compile_commands.json", "[]")
  local git_source = buffer(git_repo .. "/src/main.cpp")
  equal(git_repo .. "/build", project.resolve(git_source), "build directory and Git worktree supported")

  local params = { initializationOptions = { clangdFileStatus = true } }
  project.before_init(params, { root_dir = service })
  equal(service, params.initializationOptions.compilationDatabasePath, "database sent to clangd")
  equal(true, params.initializationOptions.clangdFileStatus, "other initialization options preserved")
  local fallback = {}
  project.before_init(fallback, { root_dir = other_repo })
  equal(nil, fallback.initializationOptions, "no forced database when none exists")

  vim.lsp.config.clangd = { root_markers = { ".arc", ".git" } }
  local selected
  project.root_dir(header, function(root)
    selected = root
  end)
  equal(second, selected, "header attaches to the selected service root")
  project.root_dir(foreign_header, function(root)
    selected = root
  end)
  equal(other_repo, selected, "normal root detection remains available")
  equal(service, project.resolve(source), "source selection remains stable")
end, debug.traceback)

vim.fn.chdir(original_cwd)
vim.fn.delete(temp, "rf")
if not ok then
  error(err)
end
print("clangd project selection: " .. checks .. " checks passed")
