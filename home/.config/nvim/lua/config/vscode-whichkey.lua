-- Keep native Neovim mappings as the source of truth. Which Key only takes
-- focus when an incomplete prefix times out; complete sequences run normally.
local M = {}
local mappings = { n = {}, x = {} }
local groups = { a = "Codex", b = "Buffers", c = "Code", f = "Files", s = "Search" }

function M.map(mode, lhs, rhs, opts)
  vim.keymap.set(mode, lhs, rhs, opts)
  local suffix = lhs:match("^<leader>(.+)$")
  if not suffix then
    return
  end
  for _, item in ipairs(type(mode) == "table" and mode or { mode }) do
    if mappings[item] then
      mappings[item][suffix] = opts.desc
    end
  end
end

local function tree(mode)
  local root = { children = {} }
  for suffix, desc in pairs(mappings[mode]) do
    local node = root
    for i = 1, #suffix do
      local key = suffix:sub(i, i)
      node.children[key] = node.children[key] or { children = {}, prefix = suffix:sub(1, i) }
      node = node.children[key]
    end
    node.desc = desc
  end
  return root
end

local function menu(node)
  local items = {}
  for _, key in ipairs(vim.tbl_keys(node.children)) do
    local child = node.children[key]
    if child.desc then
      -- A mapping can also be a prefix (notably y/yy). Execute it directly
      -- so native operator-pending mode still accepts any motion or another y.
      items[#items + 1] = {
        key = key,
        name = child.desc,
        type = "command",
        command = "vscode-neovim.send",
        args = (vim.g.mapleader or "\\") .. child.prefix,
      }
    else
      items[#items + 1] = {
        key = key,
        name = "+" .. (groups[child.prefix] or child.prefix),
        type = "bindings",
        bindings = menu(child),
      }
    end
  end
  table.sort(items, function(a, b)
    return a.key < b.key
  end)
  return items
end

function M.setup()
  for _, mode in ipairs({ "n", "x" }) do
    local function install(node)
      -- Never replace a real mapping with a menu, including the y operator.
      if node.desc then
        return
      end
      local lhs = "<leader>" .. (node.prefix or "")
      if vim.fn.maparg(lhs, mode) == "" then
        vim.keymap.set(mode, lhs, function()
          -- An unmatched next key (including Escape) also resolves a prefix.
          -- Leave that input to Neovim instead of opening a stale popup.
          if vim.fn.getchar(1) ~= 0 then
            return
          end
          require("vscode").action("whichkey.show", {
            args = { menu(node) },
            callback = function(err)
              if err then
                vim.notify("Which Key: install VSpaceCode.whichkey in VS Code. " .. tostring(err), vim.log.levels.WARN)
              end
            end,
          })
        end, { desc = "Which Key: " .. (groups[node.prefix] or "Leader"), nowait = false })
      end
      for _, child in pairs(node.children) do
        install(child)
      end
    end
    install(tree(mode))
  end
end

return M
