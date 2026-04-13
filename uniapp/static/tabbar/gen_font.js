/**
 * 生成 tabBar 用的 iconfont TTF 文件
 * E001=首页(房子) E002=查找(放大镜) E003=策略(折线图) E004=我的(人物)
 */
const fs = require('fs')
const path = require('path')
const SVGIcons2SVGFontStream = require('svgicons2svgfont')
const svg2ttf = require('svg2ttf')
const { Readable } = require('stream')

const icons = [
  {
    name: 'home',
    unicode: '\uE001',
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
      <path d="M512 128L64 480h128v384h224V608h192v256h224V480h128L512 128z" fill="currentColor"/>
    </svg>`
  },
  {
    name: 'search',
    unicode: '\uE002',
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
      <circle cx="420" cy="420" r="280" fill="none" stroke="currentColor" stroke-width="80"/>
      <line x1="620" y1="620" x2="900" y2="900" stroke="currentColor" stroke-width="80" stroke-linecap="round"/>
    </svg>`
  },
  {
    name: 'strategy',
    unicode: '\uE003',
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
      <polyline points="80,800 280,400 480,580 720,180 940,320" fill="none" stroke="currentColor" stroke-width="72" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`
  },
  {
    name: 'my',
    unicode: '\uE004',
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
      <circle cx="512" cy="300" r="200" fill="currentColor"/>
      <path d="M160 900c0-200 160-320 352-320s352 120 352 320" fill="currentColor"/>
    </svg>`
  }
]

async function generate() {
  // Step 1: SVG icons -> SVG font
  const svgFont = await new Promise((resolve, reject) => {
    const fontStream = new SVGIcons2SVGFontStream({
      fontName: 'tabbar-icons',
      normalize: true,
      fontHeight: 1024,
      centerHorizontally: true,
    })

    let result = ''
    fontStream.on('data', chunk => { result += chunk.toString() })
    fontStream.on('end', () => resolve(result))
    fontStream.on('error', reject)

    for (const icon of icons) {
      const glyph = new Readable()
      glyph._read = function() {}
      glyph.push(icon.svg)
      glyph.push(null)
      glyph.metadata = {
        name: icon.name,
        unicode: [icon.unicode],
      }
      fontStream.write(glyph)
    }
    fontStream.end()
  })

  // Step 2: SVG font -> TTF
  const ttf = svg2ttf(svgFont, {})
  const ttfBuffer = Buffer.from(ttf.buffer)
  const outPath = path.join(__dirname, 'tabbar-icons.ttf')
  fs.writeFileSync(outPath, ttfBuffer)
  console.log(`Generated: ${outPath} (${ttfBuffer.length} bytes)`)
}

generate().catch(err => {
  console.error('Error:', err)
  process.exit(1)
})
