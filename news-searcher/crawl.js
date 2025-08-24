const express = require('express');
const { chromium } = require('playwright');

const app = express();
app.use(express.json());

app.post('/crawl', async (req, res) => {
  const { url } = req.body;

  if (!url) {
    console.error('[❌] Missing "url" in request body');
    return res.status(400).json({ error: 'Missing URL' });
  }

  console.log(`[�] Received crawl request for: ${url}`);

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    console.time('[⏱] Page load time');

    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });

    console.timeEnd('[⏱] Page load time');
    console.log(`[✅] Loaded page: ${url}`);

    const html = await page.content();

    console.log(`[�] Extracted HTML content from: ${url}`);
    await browser.close();
    console.log(`[�] Browser closed`);

    res.json({ success: true, html });
  } catch (err) {
    await browser.close();
    console.error(`[❌] Error crawling ${url}:`, err.message);
    res.status(500).json({ error: err.message });
  }
});

const PORT = 11236;
app.listen(PORT, () => {
  console.log(`� Playwright server running at http://localhost:${PORT}`);
});
