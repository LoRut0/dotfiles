-- Loaded only by config.keymaps inside vscode-neovim.
local vscode = require("vscode")
local whichkey = require("config.vscode-whichkey")
local map = whichkey.map

-- The extension provides a clipboard that also works across remote workspaces.
vim.g.clipboard = vim.g.vscode_clipboard
map("n", "<leader>y", '"+y', { desc = "Copy to Clipboard (then motion / y for line)" })
map("x", "<leader>y", '"+y', { desc = "Copy Selection to Clipboard" })
map("n", "<leader>yy", '"+yy', { desc = "Copy Line to Clipboard" })

local function action(mode, lhs, command, desc)
  map(mode, lhs, function()
    vscode.action(command)
  end, { desc = desc })
end

action("n", "<leader>ff", "workbench.action.quickOpen", "Find Files")
action("n", "<leader>sg", "workbench.action.findInFiles", "Grep")
action("n", "<leader>e", "workbench.view.explorer", "Explorer")

-- Keep LazyVim's VS Code aliases in the same menu as our custom mappings.
action("n", "<leader> ", "workbench.action.quickOpen", "Find Files")
action("n", "<leader>/", "workbench.action.findInFiles", "Grep")
action("n", "<leader>ss", "workbench.action.gotoSymbol", "Document Symbols")
action("n", "<leader>ft", "workbench.action.terminal.toggleTerminal", "Toggle Terminal")
action("n", "<leader>fT", "workbench.action.terminal.toggleTerminal", "Toggle Terminal")

-- Manage VS Code tabs instead of the extension's internal Neovim buffers.
action("n", "<leader>bd", "workbench.action.closeActiveEditor", "Delete Buffer")
action("n", "<leader>br", "workbench.action.closeEditorsToTheRight", "Delete Buffers to the Right")
action("n", "<leader>bl", "workbench.action.closeEditorsToTheLeft", "Delete Buffers to the Left")
action("n", "<leader>bo", "workbench.action.closeOtherEditors", "Delete Other Buffers in Group")
map("n", "<leader>bi", function()
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
map("n", "gr", function()
  vscode.action("editor.action.goToReferences")
end, { desc = "References", nowait = true })
map("n", "gai", function()
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

whichkey.setup()
