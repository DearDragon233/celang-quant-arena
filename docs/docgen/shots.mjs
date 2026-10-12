// 用 Playwright 批量截取系统页面（带登录态）
import { chromium } from 'playwright'

const BASE = 'http://127.0.0.1:8002'

async function login(page, username, password) {
  const resp = await fetch(`${BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  const data = await resp.json()
  return data.access_token
}

const run = async () => {
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
  const page = await ctx.newPage()

  const userToken = await login(page, 'trader01', '123456')
  const adminToken = await login(page, 'admin', 'admin123')

  const shots = [
    { file: '01-login.png', path: '/login', token: null },
    { file: '02-market.png', path: '/portal/market', token: userToken },
    { file: '14-pulse.png', path: '/portal/pulse', token: userToken },
    { file: '15-holdings.png', path: '/portal/holdings', token: userToken },
    { file: '16-pnl.png', path: '/portal/pnl', token: userToken },
    { file: '03-advisor.png', path: '/portal/advisor', token: userToken },
    { file: '04-trade.png', path: '/portal/trade', token: userToken },
    { file: '05-quant.png', path: '/portal/quant', token: userToken },
    { file: '06-overview.png', path: '/portal/overview', token: userToken },
    { file: '07-ranking.png', path: '/portal/ranking', token: userToken },
    { file: '10-npc.png', path: '/portal/npc', token: userToken },
    { file: '11-news.png', path: '/portal/news', token: userToken },
    { file: '12-contest.png', path: '/portal/ranking', token: userToken },
    { file: '13-contest-mgmt.png', path: '/admin/contest-mgmt', token: adminToken },
    { file: '08-dashboard.png', path: '/admin/dashboard', token: adminToken },
    { file: '09-settings.png', path: '/admin/settings', token: adminToken },
  ]

  for (const s of shots) {
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
    await page.evaluate((token) => {
      localStorage.clear()
      if (token) {
        localStorage.setItem('fin_token', token)
        localStorage.setItem('fin_user', JSON.stringify({
          id: 1, username: 'tmp', nickname: '截图', role: token.startsWith('ey') && localStorage.getItem('__role') === 'admin' ? 'admin' : 'user',
        }))
      }
    }, s.token).catch(() => {})

    // admin/user 角色需要正确的 role 才能通过路由守卫
    if (s.path.startsWith('/admin')) {
      await page.evaluate(() => {
        const u = JSON.parse(localStorage.getItem('fin_user') || '{}')
        u.role = 'admin'
        localStorage.setItem('fin_user', JSON.stringify(u))
      })
    } else if (s.token) {
      await page.evaluate(() => {
        const u = JSON.parse(localStorage.getItem('fin_user') || '{}')
        u.role = 'user'
        u.nickname = '赵启明'
        u.school = '中国农业大学'
        localStorage.setItem('fin_user', JSON.stringify(u))
      })
    }

    await page.goto(BASE + s.path, { waitUntil: 'networkidle' }).catch(() => {})
    await page.waitForTimeout(2600)
    await page.screenshot({ path: 'img/' + s.file })
    console.log('shot:', s.file)
  }

  await browser.close()
}

run()
