-- disabling
if true then
  return {}
end

-- ~/.config/nvim/lua/plugins/comment.lua
return {
  "numToStr/Comment.nvim",
  opts = {
    toggler = {
      line = "<leader>/", -- instead of gcc
      block = "<leader>b", -- instead of gb
    },
    opleader = {
      line = "<leader>/",
      block = "<leader>b",
    },
  },
}
