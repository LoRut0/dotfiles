local M = {}
local arcadia = require("config.arcadia")

local function context()
  local cwd = vim.uv.cwd()
  local file = vim.bo.buftype == "" and vim.api.nvim_buf_get_name(0) or ""
  local path = file ~= "" and file or cwd
  local arc_root = arcadia.find_root(path)
  if arc_root then
    local scope = arcadia.find_root(cwd) == arc_root and cwd or vim.fs.dirname(path)
    return "arc", scope
  end
  local git_root = vim.fs.root(path, ".git")
  if git_root then
    return "git", git_root
  end
  arc_root = arcadia.find_root(cwd)
  if arc_root then
    return "arc", cwd
  end
  git_root = vim.fs.root(cwd, ".git")
  if git_root then
    return "git", git_root
  end
end

local function run(cmd, cwd)
  local result = vim.system(cmd, { cwd = cwd, text = true }):wait(15000)
  if not result or result.code ~= 0 then
    Snacks.notify.error((result and vim.trim(result.stderr or "") or "Timed out") .. "\n" .. table.concat(cmd, " "))
    return
  end
  return result.stdout or ""
end

local function lines(output)
  return vim.split(output, "\n", { plain = true, trimempty = true })
end

local function arc_items(scope, branch)
  local cmd = branch and { "arc", "diff", "-B", "--name-status", "--relative=." }
    or { "arc", "status", "--short", "-u", "all", "." }
  local output = run(cmd, scope)
  if not output then
    return {}
  end
  local items = {}
  for _, line in ipairs(lines(output)) do
    local status, path
    if branch then
      status, path = line:match("^(%S+)%s+(.+)$")
    elseif #line >= 4 then
      status, path = line:sub(1, 2), line:sub(4)
    end
    if path then
      path = path:match(" -> (.+)$") or path:match("[^\t]+$") or path
      items[#items + 1] = {
        text = path,
        file = vim.fs.normalize(scope .. "/" .. path),
        path = path,
        status = status,
      }
    end
  end
  return items
end

local function arc_preview(ctx, scope, branch)
  local item = ctx.item
  if item.status == "??" then
    return Snacks.picker.preview.file(ctx)
  end
  local commands = {}
  if branch then
    commands[#commands + 1] = { cmd = { "arc", "diff", "-B", "--no-color", "--relative=.", "--", item.path } }
  else
    if item.status:sub(2, 2) ~= " " then
      commands[#commands + 1] = {
        title = "Unstaged changes",
        cmd = { "arc", "diff", "--no-color", "--relative=.", "--", item.path },
      }
    end
    if item.status:sub(1, 1) ~= " " then
      commands[#commands + 1] = {
        title = "Staged changes",
        cmd = { "arc", "diff", "--cached", "--no-color", "--relative=.", "--", item.path },
      }
    end
  end
  local results, remaining = {}, #commands
  ctx.preview:set_lines({ "Loading diff…" })
  for index, command in ipairs(commands) do
    vim.system(command.cmd, { cwd = scope, text = true }, function(result)
      results[index] = result
      remaining = remaining - 1
      if remaining ~= 0 then
        return
      end
      vim.schedule(function()
        if not ctx.preview.win:valid() or ctx.preview.item ~= item then
          return
        end
        local output = {}
        for i, part in ipairs(results) do
          if part.code ~= 0 then
            output[#output + 1] = vim.trim(part.stderr or "arc diff failed")
          elseif part.stdout and part.stdout ~= "" then
            if commands[i].title then
              output[#output + 1] = commands[i].title
            end
            vim.list_extend(output, lines(part.stdout))
          end
        end
        ctx.preview:set_lines(#output > 0 and output or { "No text diff for this file" })
        ctx.preview:highlight({ ft = "diff" })
      end)
    end)
  end
end

local function open_arc(scope, branch)
  return Snacks.picker({
    title = branch and "Arcadia branch changes" or "Arcadia working changes",
    finder = function()
      return arc_items(scope, branch)
    end,
    format = function(item)
      return { { ("%-3s "):format(item.status), "Comment" }, { item.path } }
    end,
    preview = function(ctx)
      arc_preview(ctx, scope, branch)
    end,
    focus = "list",
    show_empty = true,
    matcher = { sort_empty = false },
    actions = {
      refresh_arc = function(picker)
        picker:find()
      end,
    },
    win = { list = { keys = { r = "refresh_arc" } } },
    confirm = function(picker, item)
      if not item then
        return
      end
      if vim.fn.filereadable(item.file) == 0 then
        return Snacks.notify.warn("File is absent from the working tree: " .. item.path)
      end
      picker:close()
      vim.cmd.edit(vim.fn.fnameescape(item.file))
    end,
  })
end

local function git_base(root)
  local result = vim
    .system({ "git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD" }, {
      cwd = root,
      text = true,
    })
    :wait(5000)
  local candidates = {
    result and result.code == 0 and vim.trim(result.stdout or "") or "",
    "origin/main",
    "origin/master",
    "origin/trunk",
    "main",
    "master",
    "trunk",
  }
  for _, candidate in ipairs(candidates) do
    if candidate ~= "" then
      local check = vim
        .system({ "git", "rev-parse", "--verify", "--quiet", candidate .. "^{commit}" }, {
          cwd = root,
          text = true,
        })
        :wait(5000)
      if check and check.code == 0 then
        return candidate
      end
    end
  end
end

function M.open(branch)
  local vcs, scope = context()
  if vcs == "arc" then
    return open_arc(scope, branch)
  end
  if vcs == "git" then
    if branch then
      local base = git_base(scope)
      if not base then
        return Snacks.notify.error("Could not find the Git base branch")
      end
      return vim.cmd({ cmd = "DiffviewOpen", args = { base .. "...HEAD" } })
    end
    return vim.cmd("DiffviewOpen")
  end
  Snacks.notify.warn("Open a file in an Arcadia or Git checkout")
end

return M
