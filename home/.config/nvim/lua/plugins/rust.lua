return {
  "mrcjkb/rustaceanvim",
  opts = {
    server = {
      default_settings = {
        ["rust-analyzer"] = {
          diagnostics = {
            disabled = { "unlinked-file" },
          },
        },
      },
    },
  },
}
