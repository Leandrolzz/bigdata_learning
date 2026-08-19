// 高亮引擎回归测试：验证 hl() 不丢失、不损坏任何字符
// 用法: node tools/hl_test.js

const fs = require('fs');
const src = fs.readFileSync(__dirname + '/../static/js/app.js', 'utf8');

// 从 app.js 中提取 hl 函数与其依赖的常量
function extract(name) {
  const start = src.indexOf('const ' + name + ' =');
  const end = src.indexOf(';', start);
  return src.slice(start, end + 1);
}
const kwBlock = extract('PY_KW') + '\n' + extract('PY_BF') + '\n' + extract('SQL_KW');
const hlStart = src.indexOf('function hl(');
const hlEnd = src.indexOf('\nfunction codeHtml', hlStart);
const hlFn = src.slice(hlStart, hlEnd);

eval(kwBlock + '\n' + hlFn + '\n globalThis.hl = hl;');

const strip = h => h.replace(/<[^>]+>/g, '')
  .replace(/&gt;/g, '>').replace(/&lt;/g, '<').replace(/&amp;/g, '&');
const samples = [
  ['print("Hello")', 'py'],
  ['a = "x1"; b = 10; c = "y2"', 'py'],
  ['SELECT name, age FROM users WHERE age > 18 ORDER BY age DESC;', 'sql'],
  ['# 注释 123\ns = "abc123"\nprint(s, 42)', 'py'],
  ['print("a\\"b")', 'py'],
  ['x = 3.14\ny = "pi=" + str(x)', 'py'],
  ['print(\'单引号\', "双引号", 100, 3.5)', 'py'],
  ['-- SQL 注释\nSELECT COUNT(*) AS cnt FROM t WHERE name LIKE "a%"', 'sql'],
];
let ok = true;
for (const [code, lang] of samples) {
  const out = hl(code, lang);
  const plain = strip(out);
  if (plain !== code) { ok = false; console.log('FAIL:', JSON.stringify(code), '=>', JSON.stringify(plain)); }
  else console.log('PASS:', JSON.stringify(code.slice(0, 44)));
}
console.log(ok ? '✅ 高亮引擎回归全部通过' : '❌ 有失败');
process.exit(ok ? 0 : 1);
