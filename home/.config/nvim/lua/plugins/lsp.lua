return {
  "neovim/nvim-lspconfig",
  opts = {
    servers = {
      basedpyright = {
        settings = {
          basedpyright = {
            typeCheckingMode = "basic", -- or "off"
          },
        },
      },
      -- clangd = {
      --   cmd = {
      --     "clangd",
      --     "--background-index",
      --     "--clang-tidy",
      --     "--fallback-style=llvm",
      --     "--tweaks=-std=c++23",
      --   },
      -- },
    },
  },
}
