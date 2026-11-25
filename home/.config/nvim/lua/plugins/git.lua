return {
  "lewis6991/gitsigns.nvim",
  cmd = "Gitsigns",
  opts = function()
    vim.keymap.del("n", "<leader>uG")
    Snacks.toggle.get("git_signs"):map("<leader>ugs")
  end,
}
