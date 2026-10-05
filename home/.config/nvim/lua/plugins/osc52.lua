return {
  {
    "ojroques/nvim-osc52",
    cond = function()
      return not vim.g.vscode
    end,
    config = function()
      require("osc52").setup()
    end,
  },
}
