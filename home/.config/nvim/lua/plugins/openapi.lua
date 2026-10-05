return {
  "akyrey/openapi-navigator.nvim",
  cond = function()
    return not vim.g.vscode
  end,
  opts = {
    laravel = { enabled = false },
  },
}
