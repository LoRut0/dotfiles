-- Loaded only by config.keymaps inside vscode-neovim.
local vscode = require("vscode")

-- The extension provides a clipboard that also works across remote workspaces.
vim.g.clipboard = vim.g.vscode_clipboard
vim.keymap.set({ "n", "x" }, "<leader>y", '"+y', { desc = "Copy to Clipboard" })
vim.keymap.set("n", "<leader>yy", '"+yy', { desc = "Copy Line to Clipboard" })

local function action(mode, lhs, command, desc)
  vim.keymap.set(mode, lhs, function()
    vscode.action(command)
  end, { desc = desc })
end

action("n", "<leader>ff", "workbench.action.quickOpen", "Find Files")
action("n", "<leader>sg", "workbench.action.findInFiles", "Grep")
action("n", "<leader>e", "workbench.view.explorer", "Explorer")
action("n", "gb", "workbench.action.navigateBack", "Go Back")
action("n", "gB", "workbench.action.navigateForward", "Go Forward")
action("n", "gd", "editor.action.revealDefinition", "Go to Definition")
vim.keymap.set("n", "gr", function()
  vscode.action("editor.action.goToReferences")
end, { desc = "References", nowait = true })
vim.keymap.set("n", "gai", function()
  vscode.call("editor.showCallHierarchy")
  vscode.action("editor.showIncomingCalls")
end, { desc = "Calls Incoming" })
action({ "n", "x" }, "<leader>ca", "editor.action.quickFix", "Code Action")
action("n", "<leader>cr", "editor.action.rename", "Rename")
action("n", "<leader>cf", "editor.action.formatDocument", "Format Document")
action("x", "<leader>cf", "editor.action.formatSelection", "Format Selection")

action("n", "<leader>ax", "chatgpt.openSidebar", "Open Codex")
action("n", "<leader>ab", "chatgpt.addFileToThread", "Add current file to Codex")
action("x", "<leader>as", "chatgpt.addToThread", "Add selection range to Codex")
