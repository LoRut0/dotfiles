return {
  {
    -- disabling inlay hints
    "neovim/nvim-lspconfig",
    opts = {
      inlay_hints = {
        enabled = false,
        exclude = { "vue" }, -- filetypes for which you don't want to enable inlay hints
      },
    },
  },
  -- Auto pairs Automatically inserts a matching closing character when you type an opening character like ", [, or (.
  {
    "nvim-mini/mini.pairs",
    enabled = false,
  },
}
