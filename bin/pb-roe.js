#!/usr/bin/env node
/**
 * pb-roe-skill — Node CLI wrapper for the Python-based PB-ROE Claude Skill.
 *
 * Subcommands:
 *   install        Copy skill to ~/.claude/skills/pb-roe-stock-selection/ + install pip deps
 *   uninstall      Remove from ~/.claude/skills/
 *   postinstall    (internal, called by npm) Try install, never fail npm
 *   help           Show usage
 *   <args>         Default: pass through to Python entry point
 *
 * Examples:
 *   npx pb-roe-skill install
 *   pb-roe                              # run with default settings
 *   pb-roe --mode loose --top-n 10
 *   pb-roe --industry 食品饮料 --output ~/my.html
 */

'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawnSync } = require('child_process');

const PKG_ROOT = path.resolve(__dirname, '..');
const SKILL_DIR = path.join(os.homedir(), '.claude', 'skills', 'pb-roe-stock-selection');
const PKG_NAME = 'pb-roe-skill';
let PKG_VERSION = '0.0.0';
try {
  PKG_VERSION = require(path.join(PKG_ROOT, 'package.json')).version;
} catch (e) {}

const C = {
  reset: '\x1b[0m', bold: '\x1b[1m', dim: '\x1b[2m',
  red: '\x1b[31m', green: '\x1b[32m', yellow: '\x1b[33m',
  blue: '\x1b[34m', cyan: '\x1b[36m',
};
const isTTY = process.stdout.isTTY;
const c = (color, s) => (isTTY ? `${C[color]}${s}${C.reset}` : s);

function log(msg) { console.log(msg); }
function step(msg) { log(c('cyan', '▸ ') + msg); }
function ok(msg)   { log(c('green', '✓ ') + msg); }
function warn(msg) { log(c('yellow', '⚠ ') + msg); }
function fail(msg) { log(c('red', '✗ ') + msg); }

function findPython() {
  const candidates = process.platform === 'win32'
    ? ['python', 'python3', 'py']
    : ['python3', 'python'];
  for (const cmd of candidates) {
    const r = spawnSync(cmd, ['--version'], { encoding: 'utf8' });
    if (r.status === 0) {
      const out = (r.stdout || r.stderr || '').trim();
      const m = out.match(/(\d+)\.(\d+)\.(\d+)/);
      if (m && Number(m[1]) >= 3 && Number(m[2]) >= 9) {
        return { cmd, version: out };
      }
    }
  }
  return null;
}

function copyDir(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    if (['node_modules', '.git', '__pycache__', '.cache'].includes(entry.name)) continue;
    const srcPath = path.join(src, entry.name);
    const dstPath = path.join(dst, entry.name);
    if (entry.isDirectory()) {
      copyDir(srcPath, dstPath);
    } else if (entry.isFile()) {
      fs.copyFileSync(srcPath, dstPath);
    }
  }
}

function copyFileIfExists(src, dst) {
  if (fs.existsSync(src)) {
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    fs.copyFileSync(src, dst);
    return true;
  }
  return false;
}

function pipInstall(python) {
  const reqs = path.join(PKG_ROOT, 'requirements.txt');
  if (!fs.existsSync(reqs)) {
    warn('未找到 requirements.txt，跳过依赖安装');
    return true;
  }

  // Try uv first (faster)
  const uv = spawnSync('uv', ['--version'], { encoding: 'utf8' });
  if (uv.status === 0) {
    const r = spawnSync('uv', ['pip', 'install', '--system', '-r', reqs], { stdio: 'inherit' });
    if (r.status === 0) return true;
    warn('uv 安装失败，回退到 pip');
  }

  // pip strategies in order
  const strategies = [
    [python, '-m', 'pip', 'install', '--user', '-r', reqs, '--quiet'],
    [python, '-m', 'pip', 'install', '-r', reqs, '--quiet', '--break-system-packages'],
    [python, '-m', 'pip', 'install', '-r', reqs, '--quiet'],
  ];
  for (const argv of strategies) {
    const [cmd, ...args] = argv;
    const r = spawnSync(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'], encoding: 'utf8' });
    if (r.status === 0) return true;
  }
  return false;
}

function verifyImports(python) {
  const r = spawnSync(python, ['-c', 'import akshare, pandas, jinja2'], { encoding: 'utf8' });
  return r.status === 0;
}

function doInstall(opts = {}) {
  log('');
  log(c('bold', `${PKG_NAME} v${PKG_VERSION} — 安装到 Claude Code Skills`));
  log('');

  step('检查 Python 3.9+');
  const py = findPython();
  if (!py) {
    fail('未找到 Python 3.9+');
    log('  请先安装 Python: https://www.python.org/downloads/');
    log('  macOS: brew install python');
    return 1;
  }
  ok(`找到 ${py.version}`);

  step(`复制 skill 文件到 ${SKILL_DIR}`);
  if (fs.existsSync(SKILL_DIR)) {
    if (opts.force) {
      fs.rmSync(SKILL_DIR, { recursive: true, force: true });
    } else {
      warn(`目标已存在，跳过文件复制（用 --force 覆盖）`);
    }
  }
  if (!fs.existsSync(SKILL_DIR)) {
    fs.mkdirSync(SKILL_DIR, { recursive: true });
    for (const f of ['SKILL.md', 'README.md', 'LICENSE', 'requirements.txt', 'install.sh']) {
      copyFileIfExists(path.join(PKG_ROOT, f), path.join(SKILL_DIR, f));
    }
    if (fs.existsSync(path.join(PKG_ROOT, 'scripts'))) {
      copyDir(path.join(PKG_ROOT, 'scripts'), path.join(SKILL_DIR, 'scripts'));
    }
    try { fs.chmodSync(path.join(SKILL_DIR, 'scripts', 'run_pb_roe.py'), 0o755); } catch (e) {}
    ok('文件已复制');
  }

  step('安装 Python 依赖（akshare/pandas/jinja2，首次约 1-3 分钟）');
  if (pipInstall(py.cmd)) {
    ok('依赖安装完成');
  } else {
    warn('依赖安装失败，请手动运行：');
    log(c('dim', `    ${py.cmd} -m pip install --user -r ${path.join(PKG_ROOT, 'requirements.txt')}`));
  }

  step('验证导入');
  if (verifyImports(py.cmd)) {
    ok('akshare / pandas / jinja2 全部 OK');
  } else {
    warn('依赖导入验证失败，CLI 仍可尝试运行（首次会报错提醒）');
  }

  log('');
  log(c('green', c('bold', '✅ 安装完成')));
  log('');
  log(c('bold', '使用方式：'));
  log('');
  log('  ' + c('cyan', '在 Claude Code 中说一句话即可：'));
  log('    "帮我跑 PB-ROE 选股"');
  log('');
  log('  ' + c('cyan', '或命令行直接运行：'));
  log('    pb-roe                          # 默认 strict 模式');
  log('    pb-roe --mode loose --top-n 10');
  log('    pb-roe --industry 食品饮料');
  log('    pb-roe --help                   # 查看全部参数');
  log('');
  return 0;
}

function doUninstall() {
  if (!fs.existsSync(SKILL_DIR)) {
    warn(`未找到安装目录 ${SKILL_DIR}`);
    return 0;
  }
  fs.rmSync(SKILL_DIR, { recursive: true, force: true });
  ok(`已删除 ${SKILL_DIR}`);
  const cache = path.join(os.homedir(), '.cache', 'pb_roe_skill');
  if (fs.existsSync(cache)) {
    fs.rmSync(cache, { recursive: true, force: true });
    ok(`已清理缓存 ${cache}`);
  }
  return 0;
}

function doRun(args) {
  const py = findPython();
  if (!py) {
    fail('未找到 Python 3.9+');
    log('  先安装 Python：https://www.python.org/downloads/');
    log(`  或运行：${c('cyan', `npx ${PKG_NAME} install`)} 查看完整安装提示`);
    return 1;
  }

  // Prefer the installed skill copy if it exists; fall back to bundled package
  const candidates = [
    path.join(SKILL_DIR, 'scripts', 'run_pb_roe.py'),
    path.join(PKG_ROOT, 'scripts', 'run_pb_roe.py'),
  ];
  const script = candidates.find(p => fs.existsSync(p));
  if (!script) {
    fail('未找到 run_pb_roe.py');
    log(`  请先运行：${c('cyan', `npx ${PKG_NAME} install`)}`);
    return 1;
  }

  const r = spawnSync(py.cmd, [script, ...args], { stdio: 'inherit' });
  return r.status ?? 1;
}

function doPostinstall() {
  // Quiet best-effort install during npm install. Never fail npm itself.
  try {
    const py = findPython();
    if (!py) {
      log('');
      warn(`${PKG_NAME}: 未找到 Python 3.9+，跳过自动 Skill 安装`);
      log(c('dim', `  装好 Python 后运行：npx ${PKG_NAME} install`));
      log('');
      return 0;
    }
    if (fs.existsSync(SKILL_DIR)) {
      log('');
      log(c('dim', `${PKG_NAME}: skill 已安装于 ${SKILL_DIR}`));
      log(c('dim', `  如需更新：npx ${PKG_NAME} install --force`));
      log('');
      return 0;
    }
    return doInstall();
  } catch (e) {
    warn(`postinstall 出错（不影响 npm 安装）：${e.message}`);
    log(c('dim', `  请手动运行：npx ${PKG_NAME} install`));
    return 0;
  }
}

function showHelp() {
  log(`
${c('bold', `pb-roe-skill v${PKG_VERSION}`)} — A股 PB-ROE 价值选股 Claude Code Skill

${c('bold', '安装：')}
  npx -y github:JetQiao/stock-selection-skill install   # 推荐
  npm install -g github:JetQiao/stock-selection-skill   # 全局安装

${c('bold', '使用：')}
  pb-roe                                   # 默认 strict 模式选股
  pb-roe --mode loose                      # 宽松阈值
  pb-roe --top-n 10                        # 输出 10 只
  pb-roe --industry 食品饮料                # 限定行业
  pb-roe --output ~/my.html                # 自定义输出
  pb-roe --skip-history                    # 跳过历史 ROE 检查（更快）
  pb-roe --clear-cache                     # 清空缓存重跑
  pb-roe --no-open                         # 跑完不自动打开浏览器

${c('bold', '管理：')}
  pb-roe-skill install                     # （重新）安装 Skill
  pb-roe-skill install --force             # 覆盖已有安装
  pb-roe-skill uninstall                   # 卸载 Skill 和缓存
  pb-roe-skill --help                      # 本帮助
  pb-roe-skill --version                   # 版本号

${c('bold', '在 Claude Code 中触发：')}
  "帮我跑 PB-ROE 选股"
  "用 PB-ROE 模型选 A 股"
  "PB-ROE 选股，宽松一点的阈值"

主页: https://github.com/JetQiao/stock-selection-skill
`);
}

function main() {
  const argv = process.argv.slice(2);
  const sub = argv[0];

  switch (sub) {
    case 'install': {
      const force = argv.includes('--force') || argv.includes('-f');
      process.exit(doInstall({ force }));
    }
    case 'uninstall':
    case 'remove':
      process.exit(doUninstall());
    case 'postinstall':
      process.exit(doPostinstall());
    case '--help':
    case '-h':
    case 'help':
      showHelp();
      process.exit(0);
    case '--version':
    case '-v':
      log(PKG_VERSION);
      process.exit(0);
    default:
      process.exit(doRun(argv));
  }
}

main();
