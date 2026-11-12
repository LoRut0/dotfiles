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

-- Manage VS Code tabs instead of the extension's internal Neovim buffers.
action("n", "<leader>bd", "workbench.action.closeActiveEditor", "Delete Buffer")
action("n", "<leader>br", "workbench.action.closeEditorsToTheRight", "Delete Buffers to the Right")
action("n", "<leader>bl", "workbench.action.closeEditorsToTheLeft", "Delete Buffers to the Left")
action("n", "<leader>bo", "workbench.action.closeOtherEditors", "Delete Other Buffers in Group")
vim.keymap.set("n", "<leader>bi", function()
  vscode.eval_async([[
    const groups = vscode.window.tabGroups;
    const hidden = groups.all.flatMap(group => group.tabs.filter(tab => !tab.isActive));
    if (hidden.length > 0) {
      await groups.close(hidden, true);
    }
  ]])
end, { desc = "Delete Invisible Buffers" })

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
