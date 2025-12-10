-- Options are automatically loaded before lazy.nvim startup
-- Default options that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
-- Add any additional options here
vim.g.mapleader = "\\"
vim.g.maplocalleader = "\\"
-- disabling inline hints
vim.lsp.inlay_hint.enable(false)

--langmap for russian keyboard
vim.opt.langmap =
  "йЙцЦуУкКеЕнНгГшШщЩзЗхХъЪфФыЫвВаАпПрРоОлЛдДжЖэЭяЯчЧсСмМиИтТьЬбБюЮ.\\,;qQwWeErRtTyYuUiIoOpP[{]}aAsSdDfFgGhHjJkKlL;:'\"zZxXcCvVbBnNmM\\,<.>/?"

-- to remove highlighting
-- nnoremap <Leader>/ :noh<cr> " for highlighting after searct / or ?
-- nnoremap <Leader>/ :nohl<cr> " for highlighting after search and replace

-- tabs size
-- more of this in autocmd
vim.opt.tabstop = 4
vim.opt.shiftwidth = 4
vim.opt.expandtab = true

-- enabling wrap by default
vim.opt.wrap = true
