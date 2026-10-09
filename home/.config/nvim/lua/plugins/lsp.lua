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
      clangd = {
        root_dir = function(bufnr, on_dir)
          require("config.clangd_project").root_dir(bufnr, on_dir)
        end,
        before_init = function(params, config)
          require("config.clangd_project").before_init(params, config)
        end,
      },
    },
  },
}
