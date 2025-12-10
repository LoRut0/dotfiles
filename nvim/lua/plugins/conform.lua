return {
  "stevearc/conform.nvim",
  opts = {
    formatters_by_ft = {
      cpp = { "clang_format" },
      c = { "clang_format" },
    },
    formatters = {
      clang_format = {
        -- Use the Mason-installed binary
        command = vim.fn.expand("~/.local/share/nvim/mason/bin/clang-format"),
        prepend_args = {
          "-style=InheritParentConfig",
          "-fallback-style=WebKit",
        },
      },
    },
  },
}
