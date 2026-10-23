/** Frame original iPhone screenshots without changing their UI or text. */
const { chromium } = require('playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
(async()=>{
 const steps = [
  ['select-events.png','01','勾选要添加的事项','一张截图，多条事项分别选择'],
  ['edit-event.png','02','修改标题、时间和提醒','保存前，在原生日历表单里确认'],
  ['saved-event.png','03','在日历里查看结果','名称、时间、地点和原文一起保留']
 ];
 const figures=[];
 for(const [file,num,title,description]of steps){
  const data=(await fs.readFile(path.join(root,'docs/images',file))).toString('base64');
  figures.push(`<figure><div class="step"><span>${num}</span><h2>${title}</h2></div><p>${description}</p><div class="device"><img src="data:image/png;base64,${data}" alt="${title}"></div></figure>`);
 }
 const html=`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><style>
 *{box-sizing:border-box}body{margin:0;color:#2c253c;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;background:radial-gradient(ellipse at 92% 16%,#dceae9 0,transparent 44%),radial-gradient(ellipse at 10% 74%,#e1daf5 0,transparent 52%),#f5f3fa;-webkit-font-smoothing:antialiased}main{padding:65px 85px}.brand{display:flex;align-items:center;font-size:30px;font-weight:750;gap:12px}.icon{background:#6653d8;color:white;border-radius:14px;height:46px;width:46px;display:grid;place-items:center;font-size:34px}.tag{margin-left:auto;font-size:16px;color:#756981;font-weight:500;letter-spacing:2px}h1{font-size:67px;letter-spacing:-2px;line-height:1.22;margin:42px 0 18px}h1 em{font-style:normal;color:#6751d8}.lead{font-size:23px;color:#7a6e8b;margin:0;letter-spacing:2px}section{display:flex;justify-content:space-between;margin-top:54px;gap:50px}figure{margin:0;width:480px}.step{display:flex;align-items:center;gap:12px}.step span{display:grid;place-items:center;width:36px;height:36px;border-radius:50%;background:#e7e1f6;color:#6b52cf;font-size:16px;font-weight:650}h2{font-size:25px;margin:0}figure p{font-size:17px;color:#8b7e9a;margin:12px 0 25px 48px}.device{width:390px;margin:0 auto;background:#1b181f;border-radius:53px;border:8px solid #2a2531;box-shadow:0 28px 42px #3d2b5d20;overflow:hidden;line-height:0}.device img{width:100%;height:auto;display:block;border-radius:43px}footer{text-align:center;color:#8c809a;font-size:16px;line-height:1.9;margin-top:45px}.cost{position:absolute;right:90px;top:180px;border:1px solid #ddd4ee;background:#ffffff80;border-radius:20px;padding:21px 27px;color:#665574;font-size:18px;line-height:1.8}.cost strong{font-size:27px;color:#6751d8}
 </style><body><main><div class="brand"><span class="icon">↗</span>Snap2Cal<span class="tag">截图入历 · iPhone 实际使用界面</span></div><h1>从识别到入历，<br><em>每一步都由你确认。</em></h1><p class="lead">勾选事项 → 编辑确认 → 存入日历</p><aside class="cost">接入 DeepSeek API<br>单次约 <strong>0.5 分钱</strong><br><span style="font-size:14px">日常使用费用参考，实际按用量计费</span></aside><section>${figures.join('')}</section><footer>真机截图 · 演示事项为虚构测试数据 · 保留原始界面与文字<br>截图中为自定义的「提前 2 小时」提醒；v1.4.0 默认提前 1 小时，可自行修改。</footer></main></body></html>`;
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const page=await browser.newPage({viewport:{width:1800,height:1410},deviceScaleFactor:1});
 await page.setContent(html);await page.evaluate(()=>document.fonts.ready);
 await page.screenshot({path:path.join(root,'docs/images/overview.png'),fullPage:true});
 // Keep a small reusable layout source referencing the original files.
 let source=html;
 for(let i=0;i<steps.length;i++)source=source.replace(/src="data:image\/png;base64,[^"]+"/,`src="${steps[i][0]}"`);
 await fs.writeFile(path.join(root,'docs/images/overview.html'),source);
 await browser.close();console.log('Rendered showcase from the 3 original iPhone screenshots.');
})();
