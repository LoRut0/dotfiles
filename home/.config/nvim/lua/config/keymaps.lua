-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

if vim.g.vscode then
  require("config.vscode-keymaps")
  return
end

-- Make <Esc> exit terminal mode and return to Normal mode
vim.keymap.set("t", "<Esc>", [[<C-\><C-n>]], { desc = "Exit terminal mode" })
vim.keymap.set("n", "<leader>y", require("osc52").copy_operator, { expr = true })
vim.keymap.set("n", "<leader>yy", "<leader>c_", { remap = true })
vim.keymap.set("v", "<leader>y", require("osc52").copy_visual)

vim.keymap.set("n", "<leader>gs", function()
  require("config.source-control").open(false)
end, { desc = "Working Changes" })
vim.keymap.set("n", "<leader>gB", function()
  require("config.source-control").open(true)
end, { desc = "Branch Changes" })
