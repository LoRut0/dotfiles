local pending = {}
local group = vim.api.nvim_create_augroup("ArcDiff", { clear = true })

local function attach(buf)
  local path = vim.api.nvim_buf_get_name(buf)
  if path == "" or vim.bo[buf].filetype == "bigfile" then
    return false
  end
  local root = require("config.arcadia").find_root(path)
  if not root or vim.fn.executable("arc") ~= 1 then
    return false
  end
  local relative = vim.fs.relpath(root, path)

  local function refresh()
    -- Ignore results from before a refresh, rename, or detach.
    local request = {}
    pending[buf] = request
    local function run(args, callback)
      vim.system(
        args,
        { cwd = root, text = true, timeout = 15000 },
        vim.schedule_wrap(function(result)
          if pending[buf] == request and vim.api.nvim_buf_is_loaded(buf) then
            callback(result)
          end
        end)
      )
    end

    run({ "arc", "show", "HEAD:" .. relative }, function(blob)
      if blob.code == 0 then
        MiniDiff.set_ref_text(buf, blob.stdout)
        return
      end
      -- Only a confirmed new file has an empty base. An ignored file or a
      -- failed Arc command should not paint the entire buffer as added.
      run({ "arc", "status", "--short", "--", "./" .. relative }, function(status)
        local added = status.code == 0 and status.stdout:match("^[?ACR]")
        MiniDiff.set_ref_text(buf, added and "" or nil)
      end)
    end)
  end

  vim.api.nvim_create_autocmd({ "BufEnter", "BufWritePost", "FocusGained", "ShellCmdPost" }, {
    group = group,
    buffer = buf,
    callback = refresh,
  })
  for key, direction in pairs({ ["]h"] = "next", ["[h"] = "prev" }) do
    vim.keymap.set("n", key, function()
      if vim.wo.diff then
        vim.cmd.normal({ direction == "next" and "]c" or "[c", bang = true })
      else
        MiniDiff.goto_hunk(direction)
      end
    end, { buffer = buf, desc = direction == "next" and "Next Hunk" or "Prev Hunk" })
  end
  vim.keymap.set("n", "<leader>ghp", function()
    MiniDiff.toggle_overlay(buf)
  end, { buffer = buf, desc = "Toggle Arc Diff Inline" })
  refresh()
end

local function detach(buf)
  pending[buf] = nil
  vim.api.nvim_clear_autocmds({ group = group, buffer = buf })
  for _, key in ipairs({ "[h", "]h", "<leader>ghp" }) do
    vim.keymap.del("n", key, { buffer = buf })
  end
end

return {
  "nvim-mini/mini.diff",
  event = "LazyFile",
  cond = function()
    return not vim.g.vscode
  end,
  opts = {
    source = { name = "Arc HEAD", attach = attach, detach = detach },
    view = { style = "sign", signs = { add = "▎", change = "▎", delete = "" } },
    -- Gitsigns owns the Git mappings. Arc mappings are buffer-local above.
    mappings = {
      apply = "",
      reset = "",
      textobject = "",
      goto_first = "",
      goto_prev = "",
      goto_next = "",
      goto_last = "",
    },
  },
}
