return {
  {
    "folke/snacks.nvim",
    opts = {
      picker = {
        sources = {
          grep = { config = require("config.arcadia").configure },
          grep_word = { config = require("config.arcadia").configure },
          files = { config = require("config.arcadia").configure },
        },
      },
    },
    keys = {
      { "<leader>ff", LazyVim.pick("files", { root = false }), desc = "Find Files (cwd)" },
      { "<leader>fF", LazyVim.pick("files"), desc = "Find Files (Root Dir)" },
      { "<leader>sg", LazyVim.pick("live_grep", { root = false }), desc = "Grep (cwd)" },
      { "<leader>sG", LazyVim.pick("live_grep"), desc = "Grep (Root Dir)" },
    },
  },
}
