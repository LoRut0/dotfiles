return {
  "akyrey/openapi-navigator.nvim",
  cond = function()
    return not vim.g.vscode
  end,
  opts = function()
    local defaults = require("openapi-navigator.config").defaults
    return {
      -- Arcadia keeps shared schema fragments under docs/yaml without an openapi: header.
      patterns = vim.list_extend(vim.deepcopy(defaults.patterns), {
        "**/docs/yaml/**",
      }),
      root_markers = vim.list_extend(vim.deepcopy(defaults.root_markers), {
        "definitions.yaml",
        "definitions.yml",
      }),
      laravel = { enabled = false },
    }
  end,
}
