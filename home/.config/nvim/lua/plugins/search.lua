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
      {
        "<leader>sg",
        function()
          require("config.workspace_search").grep(false)
        end,
        desc = "Grep Workspace (local)",
      },
      {
        "<leader>sG",
        function()
          require("config.workspace_search").grep(true)
        end,
        desc = "Grep Workspace (Arcadia trunk)",
      },
      {
        "<leader>sA",
        function()
          require("config.workspace_search").arcadia_folder()
        end,
        desc = "Grep Arcadia Folder (trunk)",
      },
    },
  },
}
