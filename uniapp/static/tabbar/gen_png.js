/**
 * 生成 162x162 PNG tabBar 图标（@2x 高清，纯 Node.js）
 */
const fs = require('fs')
const zlib = require('zlib')
const path = require('path')

const SIZE = 162

function createPNG(pixels) {
  const raw = Buffer.alloc(SIZE * (1 + SIZE * 4))
  for (let y = 0; y < SIZE; y++) {
    raw[y * (1 + SIZE * 4)] = 0
    pixels.copy(raw, y * (1 + SIZE * 4) + 1, y * SIZE * 4, (y + 1) * SIZE * 4)
  }
  const compressed = zlib.deflateSync(raw, { level: 9 })
  const chunks = []
  chunks.push(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(SIZE, 0)
  ihdr.writeUInt32BE(SIZE, 4)
  ihdr[8] = 8; ihdr[9] = 6; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0
  chunks.push(makeChunk('IHDR', ihdr))
  chunks.push(makeChunk('IDAT', compressed))
  chunks.push(makeChunk('IEND', Buffer.alloc(0)))
  return Buffer.concat(chunks)
}

function makeChunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length, 0)
  const typeB = Buffer.from(type, 'ascii')
  const crcData = Buffer.concat([typeB, data])
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(crcData) >>> 0, 0)
  return Buffer.concat([len, typeB, data, crc])
}

function crc32(buf) {
  let c = 0xFFFFFFFF
  for (let i = 0; i < buf.length; i++) c = (c >>> 8) ^ crcTable[(c ^ buf[i]) & 0xFF]
  return c ^ 0xFFFFFFFF
}
const crcTable = new Int32Array(256)
for (let n = 0; n < 256; n++) {
  let c = n
  for (let k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1)
  crcTable[n] = c
}

function hexToRGBA(hex) {
  return [parseInt(hex.slice(1,3),16), parseInt(hex.slice(3,5),16), parseInt(hex.slice(5,7),16), 255]
}

function setPixel(p, x, y, rgba) {
  x = Math.round(x); y = Math.round(y)
  if (x < 0 || x >= SIZE || y < 0 || y >= SIZE) return
  const i = (y * SIZE + x) * 4
  p[i] = rgba[0]; p[i+1] = rgba[1]; p[i+2] = rgba[2]; p[i+3] = rgba[3]
}

function fillCircle(p, cx, cy, r, c) {
  const r2 = r * r
  for (let y = Math.floor(cy-r); y <= Math.ceil(cy+r); y++)
    for (let x = Math.floor(cx-r); x <= Math.ceil(cx+r); x++)
      if ((x-cx)*(x-cx)+(y-cy)*(y-cy) <= r2) setPixel(p, x, y, c)
}

function fillRect(p, x1, y1, x2, y2, c) {
  for (let y = Math.round(y1); y <= Math.round(y2); y++)
    for (let x = Math.round(x1); x <= Math.round(x2); x++)
      setPixel(p, x, y, c)
}

function clearRect(p, x1, y1, x2, y2) {
  for (let y = Math.round(y1); y <= Math.round(y2); y++)
    for (let x = Math.round(x1); x <= Math.round(x2); x++) {
      const i = (y * SIZE + x) * 4
      if (i >= 0 && i + 3 < p.length) { p[i]=0; p[i+1]=0; p[i+2]=0; p[i+3]=0 }
    }
}

function drawLine(p, x1, y1, x2, y2, w, c) {
  const dx = x2-x1, dy = y2-y1
  const len = Math.sqrt(dx*dx+dy*dy)
  const steps = Math.max(Math.ceil(len*2), 1)
  for (let i = 0; i <= steps; i++) {
    const t = i/steps
    fillCircle(p, x1+dx*t, y1+dy*t, w/2, c)
  }
}

function drawTriangle(p, x1,y1,x2,y2,x3,y3, c) {
  const minY = Math.max(0, Math.floor(Math.min(y1,y2,y3)))
  const maxY = Math.min(SIZE-1, Math.ceil(Math.max(y1,y2,y3)))
  for (let y = minY; y <= maxY; y++) {
    const xs = []
    for (const [ax,ay,bx,by] of [[x1,y1,x2,y2],[x2,y2,x3,y3],[x3,y3,x1,y1]]) {
      if ((ay<=y&&by>=y)||(by<=y&&ay>=y)) {
        if (ay===by) continue
        xs.push(ax+(y-ay)/(by-ay)*(bx-ax))
      }
    }
    xs.sort((a,b)=>a-b)
    for (let i=0;i<xs.length-1;i+=2)
      for (let x=Math.ceil(xs[i]);x<=Math.floor(xs[i+1]);x++) setPixel(p,x,y,c)
  }
}

// ===== Icons (scaled to 162) =====

function drawHome(color) {
  const p = Buffer.alloc(SIZE*SIZE*4, 0), c = hexToRGBA(color)
  drawTriangle(p, 81,16, 16,76, 146,76, c)
  fillRect(p, 30,76, 132,144, c)
  clearRect(p, 62,100, 100,144)
  return createPNG(p)
}

function drawSearch(color) {
  const p = Buffer.alloc(SIZE*SIZE*4, 0), c = hexToRGBA(color)
  const cx=62, cy=62, r=40
  for (let y=0;y<SIZE;y++)
    for (let x=0;x<SIZE;x++) {
      const d = Math.sqrt((x-cx)**2+(y-cy)**2)
      if (d >= r-6 && d <= r+6) setPixel(p, x, y, c)
    }
  drawLine(p, 92,92, 140,140, 12, c)
  return createPNG(p)
}

function drawStrategy(color) {
  const p = Buffer.alloc(SIZE*SIZE*4, 0), c = hexToRGBA(color)
  const pts = [[16,124],[44,68],[72,96],[108,30],[146,56]]
  for (let i=0;i<pts.length-1;i++)
    drawLine(p, pts[i][0],pts[i][1], pts[i+1][0],pts[i+1][1], 10, c)
  for (const [x,y] of pts) fillCircle(p, x, y, 7, c)
  return createPNG(p)
}

function drawMy(color) {
  const p = Buffer.alloc(SIZE*SIZE*4, 0), c = hexToRGBA(color)
  fillCircle(p, 81, 42, 28, c)
  for (let y=82;y<=146;y++) {
    const ry = (y-82)/64
    const w = Math.sqrt(Math.max(0, 1-(1-ry)*(1-ry))) * 60
    for (let x = Math.round(81-w); x <= Math.round(81+w); x++)
      setPixel(p, x, y, c)
  }
  return createPNG(p)
}

// ===== Generate =====
const normalColor = '#999999'
const activeColor = '#007aff'

const icons = { home: drawHome, search: drawSearch, strategy: drawStrategy, my: drawMy }
for (const [name, fn] of Object.entries(icons)) {
  fs.writeFileSync(path.join(__dirname, `${name}.png`), fn(normalColor))
  fs.writeFileSync(path.join(__dirname, `${name}_active.png`), fn(activeColor))
  console.log(`${name}.png + ${name}_active.png`)
}
console.log('done')
