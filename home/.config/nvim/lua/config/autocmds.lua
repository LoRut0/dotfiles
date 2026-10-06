-- Autocmds are automatically loaded on the VeryLazy event
-- Default autocmds that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/autocmds.lua
--
-- Add any additional autocmds here
-- with `vim.api.nvim_create_autocmd`
--
-- Or remove existing autocmds by their group name (which is prefixed with `lazyvim_` for the defaults)
-- e.g. vim.api.nvim_del_augroup_by_name("lazyvim_wrap_spell")

if vim.fn.has("nvim-0.12") == 1 and not vim.g.vscode then
  vim.api.nvim_create_user_command("LspRestart", function(opts)
    local args = { "restart" }
    if opts.args ~= "" then
      args[#args + 1] = opts.args
    end
    vim.cmd({ cmd = "lsp", args = args })
  end, { nargs = "?", desc = "Restart LSP clients" })
end

-- html, css, js, json, typescript, lua — 2 spaces
vim.api.nvim_create_autocmd("FileType", {
  pattern = { "html", "css", "javascript", "json", "typescript", "lua" },
  callback = function()
    vim.opt_local.tabstop = 2
    vim.opt_local.shiftwidth = 2
    vim.opt_local.softtabstop = 2
  end,
})

vim.api.nvim_create_autocmd("FileType", {
  pattern = "plantuml",
  callback = function(args)
    vim.bo[args.buf].makeprg = "java -jar ~/.local/bin/plantuml-1.2026.2.jar --svg -stdrpt:2 %"
    vim.bo[args.buf].errorformat = "%f:%l:%*[^:]:%m"
  end,
})

vim.api.nvim_create_autocmd("FileType", {
  pattern = "markdown",
  callback = function(args)
    vim.opt_local.spell = false
    vim.diagnostic.enable(false, { bufnr = args.buf })
  end,
})

if not vim.g.vscode then
  local styled_filetypes = { python = true, c = true, cpp = true, go = true, yaml = true, json = true }
  local arcadia = require("config.arcadia")

  LazyVim.format.register({
    name = "ya style",
    priority = 200,
    primary = true,
    sources = function(buf)
      local path = vim.api.nvim_buf_get_name(buf)
      local root = vim.bo[buf].buftype == "" and path ~= "" and styled_filetypes[vim.bo[buf].filetype]
        and arcadia.find_root(path)
      return root and vim.fn.executable(root .. "/ya") == 1 and { "ya style" } or {}
    end,
    format = function(buf)
      require("conform").format({
        bufnr = buf,
        formatters = { "ya_style" },
        lsp_format = "never",
        timeout_ms = 30000,
      })
    end,
  })
end
