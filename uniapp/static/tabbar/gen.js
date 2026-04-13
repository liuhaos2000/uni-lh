const fs = require('fs')
const path = require('path')
const dir = path.dirname(__filename || '.')

const icons = {
  // 首页 - 房子
  'home': {
    normal: '#999',
    active: '#007aff',
    svg: (c) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="81" height="81"><path d="M24 6L4 22h6v18h10V28h8v12h10V22h6L24 6z" fill="${c}"/></svg>`
  },
  // 查找 - 放大镜
  'search': {
    normal: '#999',
    active: '#007aff',
    svg: (c) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="81" height="81"><circle cx="20" cy="20" r="14" fill="none" stroke="${c}" stroke-width="4"/><line x1="30" y1="30" x2="42" y2="42" stroke="${c}" stroke-width="4" stroke-linecap="round"/></svg>`
  },
  // 策略 - 折线图
  'strategy': {
    normal: '#999',
    active: '#007aff',
    svg: (c) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="81" height="81"><polyline points="4,38 14,22 24,30 34,12 44,18" fill="none" stroke="${c}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg>`
  },
  // 我的 - 人物
  'my': {
    normal: '#999',
    active: '#007aff',
    svg: (c) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="81" height="81"><circle cx="24" cy="14" r="10" fill="${c}"/><path d="M6 42c0-10 8-16 18-16s18 6 18 16" fill="${c}"/></svg>`
  }
}

for (const [name, icon] of Object.entries(icons)) {
  fs.writeFileSync(path.join(__dirname, `${name}.svg`), icon.svg(icon.normal))
  fs.writeFileSync(path.join(__dirname, `${name}_active.svg`), icon.svg(icon.active))
}
console.log('done')
