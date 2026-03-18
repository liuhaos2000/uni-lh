const WebSocket = require('ws');

const wss = new WebSocket.Server({ port: 8080 });

wss.on('connection', (ws) => {
  console.log('Client connected');

  ws.on('message', (message) => {
    console.log('Received:', message);
    const data = JSON.parse(message);

    if (data.action === 'subscribe' && data.skId) {
      // 模拟数据推送
      setInterval(() => {
        const randomData = generateRandomData();
        ws.send(JSON.stringify(randomData));
      }, 5000); // 每 5 秒发送一次数据
    }
  });

  ws.on('close', () => {
    console.log('Client disconnected');
  });
});

console.log('Mock WebSocket server is running on ws://localhost:8080');

// 生成随机数据的函数
function generateRandomData() {
  const historyList = [];
  for (let i = 0; i < 5; i++) { // 生成 5 条随机数据
    const buyDate = getRandomDate();
    const sellDate = getRandomDate(buyDate);
    const warehousePosition = Math.floor(Math.random() * 1000) + 1; // 1 到 1000 之间的随机数
    const profitMargin = (Math.random() * 10).toFixed(2) + '%'; // 0.00% 到 9.99% 之间的随机百分比

    historyList.push({
      buyDate,
      sellDate,
      warehousePosition,
      profitMargin
    });
  }

  return { historyList };
}

// 生成随机日期
function getRandomDate(afterDate = null) {
  const start = afterDate && afterDate instanceof Date ? afterDate.getTime() : new Date(2023, 0, 1).getTime(); // 2023-01-01
  const end = new Date().getTime(); // 当前时间
  const randomTime = start + Math.random() * (end - start);
  return new Date(randomTime).toISOString().split('T')[0]; // 返回 YYYY-MM-DD 格式的日期
}