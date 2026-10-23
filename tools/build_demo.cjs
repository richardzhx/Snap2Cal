/** Render fictional notification fixtures; real UI screenshots are kept separately. */
const { chromium } = require('playwright');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const font = '-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans CJK SC",sans-serif';
const notices = [
 {app:'项目协作',time:'刚刚',title:'材料提交提醒',body:'请在2026年10月26日18:00前提交项目材料，提交后记得在群里确认。',color:'#6156dc'},
 {app:'团队通知',time:'5分钟前',title:'产品评审会',body:'2026年10月27日09:00在三楼会议室开会，请提前准备演示材料。',color:'#278b7b'},
 {app:'生活提醒',time:'12分钟前',title:'周末读书分享',body:'2026年10月31日14:30，社区活动室见。带上一本最近喜欢的书就好。',color:'#bf774a'}
];
function notification(n){return `<div class="notice"><div class="meta"><i style="background:${n.color}"></i>${n.app}<span>${n.time}</span></div><h3>${n.title}</h3><p>${n.body}</p></div>`}
const base=`*{box-sizing:border-box}body{margin:0;font-family:${font};color:#26213a;-webkit-font-smoothing:antialiased}.status{display:flex;justify-content:space-between;font-weight:650;padding:20px 28px;font-size:16px}.notice{background:#ffffffd9;border:1px solid #ffffffa8;border-radius:21px;padding:20px;margin-bottom:13px;text-align:left;box-shadow:0 7px 20px #2d205308}.meta{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:650;color:#625d71}.meta i{width:20px;height:20px;border-radius:6px}.meta span{margin-left:auto;font-weight:400;color:#8b8596}.notice h3{font-size:16px;margin:13px 0 6px}.notice p{font-size:14px;line-height:1.65;margin:0;color:#514c60}.demo-label{font-size:12px;color:#736b88;text-align:center}.screen{overflow:hidden;height:100%;position:relative;background:#f4f2fb}.nav{display:flex;align-items:center;justify-content:space-between;padding:20px 20px 14px;font-size:15px;font-weight:650;color:#6653d8}.nav strong{color:#2f2841}.panel{margin:16px;background:white;border-radius:18px;overflow:hidden}.row{padding:18px;border-bottom:1px solid #f0edf5;display:flex;align-items:center;gap:12px}.row:last-child{border:0}.check{border:2px solid #d3cedd;width:23px;height:23px;border-radius:50%;flex:none}.check.on{background:#6b55df;border-color:#6b55df;color:white;text-align:center;font-size:14px}.row b{font-size:14px;display:block}.row small{font-size:12px;color:#877f97;display:block;line-height:1.6;margin-top:7px}.field{padding:16px;font-size:14px;border-bottom:1px solid #f0edf5;display:flex;justify-content:space-between;gap:10px}.field span:last-child{color:#7b728d}.hint{font-size:12px;line-height:1.8;color:#847a96;margin:16px 22px}.home{position:absolute;bottom:9px;width:110px;height:5px;background:#24202a;border-radius:10px;left:50%;transform:translateX(-50%)} `;
function wrap(content,css=''){return `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><style>${base}${css}</style><body>${content}</body></html>`}
function lockContent(items){return `<div class="status"><span>09:41</span><span>▮▮▮　Wi-Fi　▰</span></div><div style="text-align:center;padding:18px 0 35px"><div style="font-size:14px">2026年10月23日　星期五</div><div style="font-size:75px;font-weight:650;letter-spacing:-4px;margin-top:4px">09:41</div></div><div style="padding:0 16px">${items.map(notification).join('')}</div>`}
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const page=await browser.newPage({viewport:{width:1800,height:1200},deviceScaleFactor:1});
 const variants=[
  ['01-multiple-notices',notices,'三条通知，分别包含截止时间、会议时间和活动时间。'],
  ['02-missing-time',[{...notices[0],title:'材料提交提醒',body:'请大家整理好本季度项目材料，提交时间稍后另行通知。'},{...notices[1],body:'2026年10月27日09:00在三楼会议室开会。'}],'第一条没有明确时间，不应借用第二条会议的日期。'],
  ['03-calendar-boundaries',[{...notices[0],title:'跨年值班交接',body:'交接时间：2027年1月1日00:05。请准时在线。'},{...notices[1],title:'闰日数据复核',body:'复核时间：2028年2月29日09:30，地点在数据中心。'},{...notices[2],title:'通知更正待确认',body:'通知写着2026年2月30日10:00，但日期可能有误，请等后续更正。'}],'明确年份应保留；不存在的日期应留空或提醒人工确认。']
 ];
 await page.setViewportSize({width:1179,height:2556});
 for(const [name,items,description]of variants){
  const html=wrap(`<div class="fixture"><div class="screen">${lockContent(items)}<div class="testmark">测试截图 · 虚构通知<br>${description}</div></div></div>`,`.fixture{width:1179px;height:2556px}.screen{background:linear-gradient(150deg,#e2dcf6,#e9f0f0)}.status{font-size:43px;padding:72px 85px 0}.screen>div:nth-child(2){padding:115px 0 110px!important}.screen>div:nth-child(2)>div:first-child{font-size:43px!important}.screen>div:nth-child(2)>div:last-child{font-size:225px!important}.screen>div:nth-child(3){padding:0 42px!important}.notice{padding:45px;border-radius:44px;margin-bottom:28px}.meta{font-size:32px;gap:18px}.meta i{height:49px;width:49px;border-radius:14px}.notice h3{font-size:44px;margin:26px 0 15px}.notice p{font-size:37px;line-height:1.7}.testmark{position:absolute;bottom:100px;left:80px;right:80px;font-size:27px;text-align:center;line-height:1.8;color:#857895}`);
  await page.setContent(html);await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(root,`tests/fixtures/${name}.png`)});
 }
 await browser.close();console.log('Rendered 3 fictional test screenshots.');
})();
