"""Web Scraper - 智能网页抓取

支持：
- 多页爬取（跟踪链接）
- JS 渲染（Playwright）
- 智能正文提取
- PDF 文件解析
"""
import re
import asyncio
from typing import Optional
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse


@dataclass
class ScrapedContent:
    """抓取结果"""
    url: str
    title: str = ""
    content: str = ""
    content_type: str = "html"  # html, pdf
    pages_scraped: int = 1
    links_found: int = 0
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content[:500] + "..." if len(self.content) > 500 else self.content,
            "content_type": self.content_type,
            "pages_scraped": self.pages_scraped,
            "links_found": self.links_found,
            "error": self.error
        }


class WebScraper:
    """智能网页抓取器"""

    # 要跳过的链接模式
    SKIP_PATTERNS = [
        r'\.(?:jpg|jpeg|png|gif|svg|ico|css|js|woff|woff2|ttf|eot)$',
        r'^(?:javascript|mailto|tel):',
        r'#',  # 锚点
        r'\?.*(?:share|print|email)',  # 分享链接
    ]

    # 导航/非正文区域的选择器
    NON_CONTENT_SELECTORS = [
        'nav', 'header', 'footer', 'aside',
        '.nav', '.navigation', '.menu', '.sidebar',
        '.header', '.footer', '.ad', '.advertisement',
        '.social', '.share', '.comment', '.comments',
        '#nav', '#navigation', '#menu', '#sidebar',
        '#header', '#footer', '#comments',
    ]

    def __init__(self, use_playwright: bool = True, max_pages: int = 5):
        """
        Args:
            use_playwright: 是否使用 Playwright 渲染 JS
            max_pages: 最多抓取页面数
        """
        self.use_playwright = use_playwright
        self.max_pages = max_pages
        self._playwright = None
        self._browser = None

    async def scrape(self, url: str, depth: int = 1) -> ScrapedContent:
        """抓取网页内容

        Args:
            url: 起始 URL
            depth: 爬取深度（1=只抓首页，2=首页+子页面）

        Returns:
            ScrapedContent
        """
        # 检查是否是 PDF
        if url.lower().endswith('.pdf') or 'pdf' in url.lower():
            return await self._scrape_pdf(url)

        # 尝试用 Playwright（JS 渲染）
        if self.use_playwright:
            try:
                return await self._scrape_with_playwright(url, depth)
            except ImportError:
                print("Playwright 未安装，回退到简单模式")
            except Exception as e:
                print(f"Playwright 失败: {e}，回退到简单模式")

        # 回退到简单 HTTP 抓取
        return await self._scrape_simple(url, depth)

    async def _scrape_with_playwright(self, url: str, depth: int) -> ScrapedContent:
        """使用 Playwright 抓取（支持 JS 渲染）"""
        from playwright.async_api import async_playwright

        all_content = []
        visited = set()
        to_visit = [url]
        base_domain = urlparse(url).netloc
        pages_scraped = 0
        all_links = set()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            while to_visit and pages_scraped < self.max_pages:
                current_url = to_visit.pop(0)
                if current_url in visited:
                    continue

                visited.add(current_url)

                try:
                    await page.goto(current_url, wait_until='networkidle', timeout=30000)
                    await asyncio.sleep(1)  # 等待动态内容加载

                    # 获取标题
                    title = await page.title() or ""

                    # 移除非正文元素
                    for selector in self.NON_CONTENT_SELECTORS:
                        try:
                            await page.evaluate(f'''
                                document.querySelectorAll("{selector}").forEach(el => el.remove());
                            ''')
                        except:
                            pass

                    # 获取正文
                    content = await page.evaluate('''
                        () => {
                            // 优先找 article 或 main
                            const article = document.querySelector('article') ||
                                           document.querySelector('main') ||
                                           document.querySelector('[role="main"]');
                            if (article) return article.innerText;
                            return document.body.innerText;
                        }
                    ''')

                    if content:
                        all_content.append(f"=== {current_url} ===\n{content}")
                        pages_scraped += 1

                    # 如果深度 > 1，收集链接
                    if depth > 1 and pages_scraped < self.max_pages:
                        links = await page.evaluate('''
                            () => Array.from(document.querySelectorAll('a[href]'))
                                       .map(a => a.href)
                                       .filter(href => href.startsWith('http'))
                        ''')

                        for link in links:
                            all_links.add(link)
                            # 只跟踪同域名链接
                            if urlparse(link).netloc == base_domain:
                                if link not in visited and not self._should_skip(link):
                                    to_visit.append(link)

                except Exception as e:
                    print(f"抓取 {current_url} 失败: {e}")

            await browser.close()

        combined = "\n\n".join(all_content)
        combined = self._clean_text(combined)

        return ScrapedContent(
            url=url,
            title=title,
            content=combined[:50000],  # 限制长度
            content_type="html",
            pages_scraped=pages_scraped,
            links_found=len(all_links)
        )

    async def _scrape_simple(self, url: str, depth: int) -> ScrapedContent:
        """简单 HTTP 抓取（无 JS 渲染）"""
        try:
            import aiohttp
            from bs4 import BeautifulSoup
        except ImportError:
            return ScrapedContent(url=url, error="需要安装 aiohttp 和 beautifulsoup4")

        all_content = []
        visited = set()
        to_visit = [url]
        base_domain = urlparse(url).netloc
        pages_scraped = 0
        all_links = set()
        title = ""

        async with aiohttp.ClientSession() as session:
            while to_visit and pages_scraped < self.max_pages:
                current_url = to_visit.pop(0)
                if current_url in visited:
                    continue

                visited.add(current_url)

                try:
                    async with session.get(current_url, timeout=30) as resp:
                        if resp.status != 200:
                            continue

                        # 检查是否是 PDF
                        content_type = resp.headers.get('content-type', '')
                        if 'pdf' in content_type:
                            return await self._scrape_pdf(current_url)

                        html = await resp.text()

                    soup = BeautifulSoup(html, 'html.parser')

                    # 获取标题
                    if not title:
                        title_tag = soup.find('title')
                        title = title_tag.get_text() if title_tag else ""

                    # 移除非正文元素
                    for selector in self.NON_CONTENT_SELECTORS:
                        for el in soup.select(selector):
                            el.decompose()

                    # 移除脚本和样式
                    for tag in soup(['script', 'style', 'noscript']):
                        tag.decompose()

                    # 获取正文
                    article = soup.find('article') or soup.find('main') or soup.find('body')
                    if article:
                        content = article.get_text(separator='\n', strip=True)
                        all_content.append(f"=== {current_url} ===\n{content}")
                        pages_scraped += 1

                    # 收集链接
                    if depth > 1 and pages_scraped < self.max_pages:
                        for a in soup.find_all('a', href=True):
                            link = urljoin(current_url, a['href'])
                            all_links.add(link)
                            if urlparse(link).netloc == base_domain:
                                if link not in visited and not self._should_skip(link):
                                    to_visit.append(link)

                except Exception as e:
                    print(f"抓取 {current_url} 失败: {e}")

        combined = "\n\n".join(all_content)
        combined = self._clean_text(combined)

        return ScrapedContent(
            url=url,
            title=title,
            content=combined[:50000],
            content_type="html",
            pages_scraped=pages_scraped,
            links_found=len(all_links)
        )

    async def _scrape_pdf(self, url: str) -> ScrapedContent:
        """抓取并解析 PDF"""
        try:
            import aiohttp
        except ImportError:
            return ScrapedContent(url=url, error="需要安装 aiohttp")

        try:
            # 下载 PDF
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=60) as resp:
                    if resp.status != 200:
                        return ScrapedContent(url=url, error=f"下载失败: HTTP {resp.status}")
                    pdf_bytes = await resp.read()

            # 解析 PDF
            content, title = self._parse_pdf_bytes(pdf_bytes)

            if not content:
                return ScrapedContent(url=url, error="PDF 解析失败，内容为空")

            return ScrapedContent(
                url=url,
                title=title or url.split('/')[-1],
                content=content[:50000],
                content_type="pdf",
                pages_scraped=1
            )

        except Exception as e:
            return ScrapedContent(url=url, error=f"PDF 处理失败: {e}")

    def parse_pdf_file(self, file_path: str) -> ScrapedContent:
        """解析本地 PDF 文件"""
        try:
            with open(file_path, 'rb') as f:
                pdf_bytes = f.read()

            content, title = self._parse_pdf_bytes(pdf_bytes)

            return ScrapedContent(
                url=f"file://{file_path}",
                title=title or file_path.split('/')[-1],
                content=content[:50000],
                content_type="pdf",
                pages_scraped=1
            )

        except Exception as e:
            return ScrapedContent(url=file_path, error=f"PDF 解析失败: {e}")

    def _parse_pdf_bytes(self, pdf_bytes: bytes) -> tuple[str, str]:
        """解析 PDF 字节内容"""
        content = ""
        title = ""

        # 尝试 pdfplumber（更好的表格支持）
        try:
            import pdfplumber
            import io

            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                # 获取元数据中的标题
                if pdf.metadata and pdf.metadata.get('Title'):
                    title = pdf.metadata['Title']

                texts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        texts.append(text)

                content = "\n\n".join(texts)

            if content:
                return self._clean_text(content), title

        except ImportError:
            pass
        except Exception as e:
            print(f"pdfplumber 解析失败: {e}")

        # 回退到 PyPDF2
        try:
            import PyPDF2
            import io

            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))

            # 获取元数据
            if reader.metadata and reader.metadata.title:
                title = reader.metadata.title

            texts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    texts.append(text)

            content = "\n\n".join(texts)

        except ImportError:
            return "", ""
        except Exception as e:
            print(f"PyPDF2 解析失败: {e}")
            return "", ""

        return self._clean_text(content), title

    def _should_skip(self, url: str) -> bool:
        """判断是否应该跳过这个链接"""
        for pattern in self.SKIP_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余空白
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        text = re.sub(r'\t+', ' ', text)

        # 移除空行
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]

        return '\n'.join(lines)


# 便捷函数
async def scrape_url(url: str, depth: int = 1, use_playwright: bool = True) -> ScrapedContent:
    """抓取 URL 内容"""
    scraper = WebScraper(use_playwright=use_playwright)
    return await scraper.scrape(url, depth)


async def scrape_pdf(url_or_path: str) -> ScrapedContent:
    """抓取 PDF（URL 或本地路径）"""
    scraper = WebScraper()
    if url_or_path.startswith(('http://', 'https://')):
        return await scraper._scrape_pdf(url_or_path)
    else:
        return scraper.parse_pdf_file(url_or_path)
