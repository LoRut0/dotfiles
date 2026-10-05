return {
  "folke/snacks.nvim",
  keys = {
    { "<leader>e", function() Snacks.explorer() end, desc = "Explorer (cwd)" },
    { "<leader>E", function() Snacks.explorer({ cwd = LazyVim.root() }) end, desc = "Explorer (Root Dir)" },
  },
  opts = {
    picker = {
      sources = {
        explorer = {
          hidden = true,
          ignored = {},
        },
      },
    },
  },
}
