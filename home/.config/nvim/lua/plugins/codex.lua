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
    win = {
      on_win = function(term)
        vim.api.nvim_create_autocmd("WinLeave", {
          group = term.augroup,
          buffer = term.buf,
          callback = function()
            local last = vim.api.nvim_buf_line_count(term.buf)
            -- Codex parks its cursor above the footer. Neovim tails a terminal from its last line.
            if vim.fn.line("w$") == last then
              vim.api.nvim_win_set_cursor(0, { last, 0 })
            end
          end,
        })
      end,
    },
  },
}
