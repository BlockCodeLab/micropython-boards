#!/usr/bin/env bun

/**
 * 按顶层逗号分割参数列表（忽略括号内的逗号）
 */
function splitParams(str) {
  const parts = [];
  let depth = 0;
  let start = 0;
  for (let i = 0; i < str.length; i++) {
    const ch = str[i];
    if (ch === '(' || ch === '[' || ch === '{') depth++;
    else if (ch === ')' || ch === ']' || ch === '}') depth--;
    else if (ch === ',' && depth === 0) {
      parts.push(str.slice(start, i));
      start = i + 1;
    }
  }
  parts.push(str.slice(start));
  return parts;
}

/**
 * 解析参数列表，返回数组，每个元素为 { id, type, value? }
 * 支持 *args, **kwargs, 单独 *
 */
function parseParams(paramsStr) {
  const paramsArray = [];
  if (!paramsStr.trim()) return paramsArray;

  const parts = splitParams(paramsStr);
  for (let part of parts) {
    part = part.trim();
    if (!part) continue;
    if (part === '*') continue; // 位置分隔符，忽略

    let id = '';
    let type = 'object';
    let defaultValue = null;

    // 处理 **kwargs
    if (part.startsWith('**')) {
      id = part.slice(2).split(/[=:]/)[0].trim();
      if (!id) continue;
      type = 'dict';
      const colonIdx = part.indexOf(':');
      if (colonIdx !== -1) {
        let afterColon = part.slice(colonIdx + 1).trim();
        const eqIdx = afterColon.indexOf('=');
        let endIdx = afterColon.length;
        if (eqIdx !== -1) endIdx = eqIdx;
        type = afterColon.slice(0, endIdx).trim();
        if (type === '') type = 'dict';
      }
      paramsArray.push({ id, type });
      continue;
    }

    // 处理 *args
    if (part.startsWith('*')) {
      id = part.slice(1).split(/[=:]/)[0].trim();
      if (!id) continue;
      type = 'tuple';
      const colonIdx = part.indexOf(':');
      if (colonIdx !== -1) {
        let afterColon = part.slice(colonIdx + 1).trim();
        const eqIdx = afterColon.indexOf('=');
        let endIdx = afterColon.length;
        if (eqIdx !== -1) endIdx = eqIdx;
        type = afterColon.slice(0, endIdx).trim();
        if (type === '') type = 'tuple';
      }
      paramsArray.push({ id, type });
      continue;
    }

    // 普通参数
    const nameMatch = part.match(/^(\w+)/);
    if (!nameMatch) continue;
    id = nameMatch[1];
    type = 'object';
    defaultValue = null;

    const colonIdx = part.indexOf(':');
    if (colonIdx !== -1) {
      let afterColon = part.slice(colonIdx + 1).trim();
      const eqIdx = afterColon.indexOf('=');
      const commaIdx = afterColon.indexOf(',');
      let endIdx = afterColon.length;
      if (eqIdx !== -1 && eqIdx < endIdx) endIdx = eqIdx;
      if (commaIdx !== -1 && commaIdx < endIdx) endIdx = commaIdx;
      type = afterColon.slice(0, endIdx).trim();
      if (type === '') type = 'object';
      let remaining = afterColon.slice(endIdx).trim();
      if (remaining.startsWith('=')) {
        defaultValue = remaining.slice(1).trim();
        if (defaultValue.endsWith(',')) defaultValue = defaultValue.slice(0, -1).trim();
      }
    } else {
      const eqIdx = part.indexOf('=');
      if (eqIdx !== -1) {
        defaultValue = part.slice(eqIdx + 1).trim();
        if (defaultValue.endsWith(',')) defaultValue = defaultValue.slice(0, -1).trim();
      }
    }

    const paramObj = { id, type };
    if (defaultValue !== null) paramObj.value = defaultValue;
    paramsArray.push(paramObj);
  }
  return paramsArray;
}

/**
 * 检测装饰器
 */
function detectDecorator(pyCode, funcStartIndex) {
  const before = pyCode.slice(0, funcStartIndex);
  const lines = before.split('\n');
  let decorators = [];
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i];
    const trimmed = line.trim();
    if (trimmed === '') continue;
    if (trimmed.startsWith('@')) {
      decorators.unshift(trimmed);
    } else {
      break;
    }
  }
  let entrypoint = false;
  let condition = false;
  for (const dec of decorators) {
    const match = dec.match(/@worker\.entry\(\s*([^)]*)\s*\)/);
    if (match) {
      const arg = match[1].trim();
      if (arg === '') entrypoint = true;
      else condition = true;
    }
  }
  return { entrypoint, condition };
}

/**
 * 提取文件开头的全局 TOML 元数据块
 */
function extractGlobalMetadata(pyCode) {
  const globalDocRegex = /^\s*(["']{3})(.*?)\1/s;
  const match = pyCode.match(globalDocRegex);
  if (!match) return null;
  let content = match[2];
  const lines = content.split(/\r?\n/);
  let minIndent = Infinity;
  for (const line of lines) {
    if (line.trim().length === 0) continue;
    const indent = line.match(/^\s*/)[0].length;
    if (indent < minIndent) minIndent = indent;
  }
  if (minIndent !== Infinity && minIndent > 0) {
    content = lines.map((line) => line.slice(minIndent)).join('\n');
  }
  try {
    return Bun.TOML.parse(content);
  } catch (err) {
    console.warn('⚠️ 全局 TOML 解析失败:', err.message);
    return null;
  }
}

/**
 * 构建 defines 数组（包含函数对象、分隔符、expands子数组）
 */
function buildDefinesArray(pyCode) {
  const funcRegex = /(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*([^:]+))?:\s*\n\s*(["']{3})(.*?)\4/gs;
  const functions = [];
  let match;
  while ((match = funcRegex.exec(pyCode)) !== null) {
    const fullMatch = match[0];
    const funcName = match[1];
    const paramsStr = match[2];
    const returnTypeRaw = match[3];
    const docstringDelim = match[4];
    let tomlContent = match[5];
    const funcStartIndex = match.index;

    const { entrypoint, condition } = detectDecorator(pyCode, funcStartIndex);
    const isAsync = /^\s*async\s+/.test(fullMatch);
    let isScript = false;
    let returnType = null;
    if (!returnTypeRaw) {
      isScript = true;
    } else {
      const trimmed = returnTypeRaw.trim();
      if (/^None\b|^NoneType\b/i.test(trimmed)) {
        isScript = false;
        returnType = null;
      } else {
        isScript = false;
        returnType = trimmed;
      }
    }

    // 去除 docstring 公共缩进
    const lines = tomlContent.split(/\r?\n/);
    let minIndent = Infinity;
    for (const line of lines) {
      if (line.trim().length === 0) continue;
      const indent = line.match(/^\s*/)[0].length;
      if (indent < minIndent) minIndent = indent;
    }
    if (minIndent !== Infinity && minIndent > 0) {
      tomlContent = lines.map((line) => line.slice(minIndent)).join('\n');
    }

    let tomlData = {};
    if (tomlContent.trim()) {
      try {
        tomlData = Bun.TOML.parse(tomlContent);
      } catch (err) {
        console.warn(`⚠️ 函数 ${funcName} TOML 解析失败:`, err.message);
      }
    }

    const paramsArray = parseParams(paramsStr);
    const funcObj = { id: funcName, ...tomlData };
    if (paramsArray.length > 0) funcObj.params = paramsArray;
    if (isAsync) funcObj.async = true;
    if (isScript) funcObj.script = true;
    if (returnType) funcObj.return = returnType;
    if (entrypoint) funcObj.entrypoint = true;
    if (condition) funcObj.condition = true;

    functions.push({ index: funcStartIndex, obj: funcObj });
  }

  // 找出特殊标记
  const lines = pyCode.split(/\r?\n/);
  let charIdx = 0;
  const specials = [];
  for (let line of lines) {
    const trimmed = line.trim();
    if (trimmed === '# expands') {
      specials.push({ index: charIdx, type: 'expands' });
    } else if (trimmed === '# ---') {
      specials.push({ index: charIdx, type: 'sep' });
    }
    charIdx += line.length + 1;
  }

  const events = [...functions, ...specials].sort((a, b) => a.index - b.index);
  const defines = [];
  let currentArray = defines;
  let inExpands = false;
  let expandsArray = null;

  for (const ev of events) {
    if (ev.type === 'expands') {
      if (!inExpands) {
        expandsArray = [];
        defines.push(expandsArray);
        currentArray = expandsArray;
        inExpands = true;
      }
    } else if (ev.type === 'sep') {
      if (currentArray) {
        currentArray.push('---');
      }
    } else if (ev.obj) {
      if (currentArray) {
        currentArray.push(ev.obj);
      }
    }
  }

  return defines;
}

/**
 * 主处理函数
 */
function processFile(pyCode) {
  const globalMeta = extractGlobalMetadata(pyCode);
  const definesArray = buildDefinesArray(pyCode);

  if (globalMeta && typeof globalMeta === 'object') {
    const topKeys = Object.keys(globalMeta);
    if (topKeys.length === 1) {
      const topKey = topKeys[0];
      if (!globalMeta[topKey]) globalMeta[topKey] = {};
      if (typeof globalMeta[topKey] !== 'object') globalMeta[topKey] = {};
      globalMeta[topKey].defines = definesArray;
    } else {
      globalMeta.defines = definesArray;
    }
    return globalMeta;
  } else {
    return { defines: definesArray };
  }
}

// 主程序
const filePath = process.argv[2];
if (!filePath) {
  console.error('用法: bun extract_toml.js <python文件路径>');
  process.exit(1);
}

const file = Bun.file(filePath);
if (!(await file.exists())) {
  console.error(`文件不存在: ${filePath}`);
  process.exit(1);
}

const fileContent = await file.text();
const result = processFile(fileContent);
console.log(JSON.stringify(result, null, 2));
