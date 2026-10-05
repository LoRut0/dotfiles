return {
  "dimfeld/codex.nvim",
  dependencies = { "folke/snacks.nvim" },
  cond = function()
    return not vim.g.vscode
  end,
  cmd = { "Codex", "CodexHere" },
  keys = {
    { "<leader>ax", "<cmd>Codex<cr>", desc = "Open Codex" },
    { "<leader>ab", "<cmd>CodexHere<cr>", desc = "Add current file to Codex" },
    { "<leader>as", ":'<,'>CodexHere<cr>", mode = "x", desc = "Add selection range to Codex" },
  },
  opts = {
    cwd = function()
      return vim.fn.getcwd(0)
    end,
  },
}
