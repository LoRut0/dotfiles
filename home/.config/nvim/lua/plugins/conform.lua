return {
  "stevearc/conform.nvim",
  opts = {
    formatters_by_ft = {
      cpp = { "clang_format" },
      c = { "clang_format" },
      rust = { "rustfmt" },
    },
    formatters = {
      ya_style = {
        command = function(_, ctx)
          local root = assert(require("config.arcadia").find_root(ctx.filename))
          return root .. "/ya"
        end,
        args = function(_, ctx)
          local args = { "style", "--stdin-filename=" .. ctx.filename, "-q" }
          if ctx.filename:match("%.ya?ml$") then
            args[#args + 1] = "--yaml"
          elseif ctx.filename:match("%.json$") then
            args[#args + 1] = "--json"
          end
          return args
        end,
        cwd = function(_, ctx)
          return require("config.arcadia").find_root(ctx.filename)
        end,
        require_cwd = true,
        stdin = true,
      },
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
