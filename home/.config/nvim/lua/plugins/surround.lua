return {
  {
    "nvim-mini/mini.surround",
    optional = true,
    keys = {
      -- Reuse mini.surround's operator and its standard prompts and spacing.
      { "<leader>W", "gsaiw", mode = "n", remap = true, desc = "Wrap Word" },
      { "<leader>W", "gsa", mode = "x", remap = true, desc = "Wrap Selection" },
    },
  },
}
