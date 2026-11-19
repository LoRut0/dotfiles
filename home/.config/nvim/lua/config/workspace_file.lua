local M = {}
local uv = vim.uv

function M.path(path, base)
  path = vim.fs.normalize(path, { expand_env = false })
  if path:sub(1, 1) ~= "/" then
    path = vim.fs.normalize((base or vim.fn.getcwd()) .. "/" .. path, { expand_env = false })
  end
  return uv.fs_realpath(path) or path
end

local function read(path)
  local file, err = io.open(path, "rb")
  assert(file, err)
  local text, read_err = file:read("*a")
  file:close()
  return assert(text, read_err)
end

-- Keep byte ranges so editing the folders array leaves the rest of the JSONC intact.
local function tokenize(text)
  local tokens = {}
  local pos = text:sub(1, 3) == "\239\187\191" and 4 or 1
  while true do
    local first = text:find("%S", pos)
    if not first then
      return tokens
    end
    local char = text:sub(first, first)
    local pair = text:sub(first, first + 1)
    if pair == "//" then
      pos = text:find("[\r\n]", first + 2) or #text + 1
    elseif pair == "/*" then
      pos = assert(text:find("*/", first + 2, true), "Unclosed JSONC comment") + 2
    else
      pos = first + 1
      if char == '"' then
        while true do
          local mark = assert(text:find('[\\"]', pos), "Unclosed JSON string")
          pos = mark + 1
          if text:sub(mark, mark) == '"' then
            break
          end
          pos = pos + 1 -- skip the escaped character
        end
      elseif not char:find("[%[%]{},:/]") then
        pos = text:find('[%s%[%]{},:/"]', pos) or #text + 1
      end
      tokens[#tokens + 1] = { first = first, last = pos - 1, value = text:sub(first, pos - 1) }
    end
  end
end

local function folder_tokens(tokens)
  local depth = 0
  local index
  for i, token in ipairs(tokens) do
    local value = token.value
    if value == "{" or value == "[" then
      depth = depth + 1
    elseif value == "}" or value == "]" then
      depth = depth - 1
    elseif depth == 1 and value:sub(1, 1) == '"' and tokens[i + 1] and tokens[i + 1].value == ":" then
      if vim.json.decode(value) == "folders" then
        assert(not index, "Workspace contains more than one folders field")
        index = i + 2
      end
    end
  end
  return index
end

function M.load(path)
  local text = read(path)
  local tokens = tokenize(text)
  local json = {}
  for i, token in ipairs(tokens) do
    local next_value = tokens[i + 1] and tokens[i + 1].value
    if token.value ~= "," or (next_value ~= "]" and next_value ~= "}") then
      json[#json + 1] = token.value
    end
  end
  local data = vim.json.decode(table.concat(json, " "))
  local index = folder_tokens(tokens)
  assert(type(data) == "table" and index and tokens[index].value == "[", "Expected a folders array in " .. path)

  local doc = { path = path, text = text, folders = {}, entries = {} }
  local entry, depth = nil, 0
  local base = vim.fs.dirname(path)
  for i = index + 1, #tokens do
    local token = tokens[i]
    local value = token.value
    if depth == 0 and value == "]" then
      doc.closing = token
      break
    elseif depth == 0 and value == "," then
      entry.comma = token
      entry = nil
    else
      if not entry then
        entry = { first = token.first }
        doc.entries[#doc.entries + 1] = entry
        local folder = data.folders[#doc.entries]
        if type(folder) == "table" and type(folder.path) == "string" and folder.path ~= "" then
          entry.path = M.path(folder.path, base)
          local name = type(folder.name) == "string" and folder.name ~= "" and folder.name or nil
          doc.folders[#doc.folders + 1] = { path = entry.path, name = name }
        end
      end
      entry.last = token.last
      if value == "{" or value == "[" then
        depth = depth + 1
      elseif value == "}" or value == "]" then
        depth = depth - 1
      end
    end
  end
  return doc
end

local function write(path, text, previous)
  local buf = vim.fn.bufnr(path)
  assert(buf < 0 or not vim.bo[buf].modified, "Save the modified workspace buffer first")
  local fd, temp, err = uv.fs_mkstemp(vim.fs.dirname(path) .. "/.nvim-workspace-XXXXXX")
  assert(fd, err or temp)
  uv.fs_close(fd)
  local ok, failure = pcall(function()
    assert(vim.fn.writefile(vim.split(text, "\n", { plain = true }), temp, "bs") == 0, "Cannot write " .. path)
    if previous then
      local stat = assert(uv.fs_stat(path))
      assert(uv.fs_chmod(temp, stat.mode % 512))
      assert(read(path) == previous, "Workspace changed on disk. Retry the command")
      assert(uv.fs_rename(temp, path))
    else
      assert(uv.fs_link(temp, path)) -- publish a new file only if its name is still free
    end
  end)
  uv.fs_unlink(temp)
  assert(ok, failure)
  if buf >= 0 and vim.api.nvim_buf_is_loaded(buf) then
    vim.cmd({ cmd = "checktime", args = { tostring(buf) } })
  end
end

function M.add(doc, path)
  local entry = vim.json.encode({ path = path })
  local last = doc.entries[#doc.entries]
  local comma = last and not last.comma
  local close = doc.closing.first
  local before = doc.text:sub(1, close - 1)
  local indent = before:match("\n([ \t]*)$")
  local insert = " " .. entry
  if indent then
    close = close - #indent
    local newline = doc.text:find("\r\n", 1, true) and "\r\n" or "\n"
    insert = indent .. "  " .. entry .. newline
  elseif #doc.entries == 0 then
    insert = entry
  end
  local text = doc.text:sub(1, close - 1)
  if comma then
    text = text:sub(1, last.last) .. "," .. text:sub(last.last + 1)
  end
  write(doc.path, text .. insert .. doc.text:sub(close), doc.text)
end

function M.remove(doc, path)
  local text = doc.text
  local cuts = {}
  local function cut(first, last)
    cuts[#cuts + 1] = { first = first, last = last }
  end
  local last_kept
  for _, entry in ipairs(doc.entries) do
    if entry.path == path then
      local first, last = entry.first, entry.last
      local comma = entry.comma
      if comma then
        if text:sub(last + 1, comma.first - 1):match("^[ \t]*$") then
          last = comma.last
        else
          cut(comma.first, comma.last)
        end
      end
      local indent = text:sub(1, first - 1):match("\n([ \t]*)$")
      local newline = indent and text:match("^[ \t]*\r?\n()", last + 1)
      if newline then
        first = first - #indent
        last = newline - 1
      end
      cut(first, last)
    else
      last_kept = entry
    end
  end
  local tail = doc.entries[#doc.entries]
  if last_kept and tail.path == path and not tail.comma then
    cut(last_kept.comma.first, last_kept.comma.last)
  end
  table.sort(cuts, function(a, b)
    return a.first > b.first
  end)
  for _, range in ipairs(cuts) do
    text = text:sub(1, range.first - 1) .. text:sub(range.last + 1)
  end
  write(doc.path, text, doc.text)
end

function M.save(path, folders)
  write(path, vim.json.encode({ folders = folders }, { indent = "  ", sort_keys = true }) .. "\n")
end

return M
