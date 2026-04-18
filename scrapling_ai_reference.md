# AI Reference Document: Scrapling Framework

**Document Version:** 1.0  
**Target Audience:** AI Language Models / Autonomous Agents  
**Subject:** Scrapling (Python Web Scraping Framework)
**Original URL:** https://github.com/D4Vinci/Scrapling
**Goal:** To provide a precise technical specification for the correct implementation and utilization of the Scrapling library.

---

## 1. Overview & Purpose
**Scrapling** is a high-level Python scraping framework designed to bridge the gap between simple HTTP request libraries (like `httpx` or `requests`) and heavy browser automation tools (like `Playwright` or `Selenium`). 

### Problems Solved:
- **Fragile Selectors:** Traditional CSS/XPath selectors break when websites update their DOM. Scrapling implements "adaptive" logic to make extraction more resilient.
- **Bot Detection:** Modern sites use fingerprinting to block headless browsers. Scrapling integrates stealth plugins and configuration to mimic human behavior.
- **Boilerplate Reduction:** It simplifies the "Fetch $\rightarrow$ Render $\rightarrow$ Parse" pipeline into a unified API.

### Differentiation:
| Library | Focus | Scrapling's Advantage |
| :--- | :--- | :--- |
| **BeautifulSoup** | Parsing only | Scrapling provides the *fetcher* and the *parser* together. |
| **Playwright** | Automation/Testing | Scrapling wraps Playwright with anti-detection and easier parsing. |
| **Scrapy** | Full-scale crawling | Scrapling is lighter, faster to set up for targeted scraping. |
| **Selenium** | Browser Automation | Scrapling is more performant and significantly harder to detect. |

---

## 2. Installation & Setup
### Installation
```bash
pip install scrapling
```
### Browser Dependencies
Since Scrapling utilizes Playwright for dynamic content, the browser binaries must be installed:
```bash
# If using the scrapling CLI
scrapling install 
# OR via playwright directly
playwright install
```
### Requirements
- **Python:** $\ge$ 3.8
- **OS:** Windows, macOS, Linux.
- **Drivers:** No manual driver management (e.g., chromedriver.exe) is required as Playwright manages binaries internally.

---

## 3. Core Concepts & Architecture
Scrapling follows a linear pipeline: **Fetcher $\rightarrow$ Response $\rightarrow$ Selector.**

1. **Fetchers:** Objects responsible for retrieving the raw content. They handle the transport layer (HTTP vs. WebSocket/CDP).
2. **Response Object:** The result of a `.fetch()` call. It encapsulates the status code, raw HTML, and provides methods to interact with the page.
3. **Selectors:** A layer sitting on top of the HTML that allows for data extraction. Unlike standard libraries, Scrapling’s selectors can be configured to be "adaptive" to handle slight DOM variations.

---

## 4. Key Features
- **Stealth/Anti-Detection:** Integrates `playwright-stealth` and custom fingerprinting to bypass DataDome, Cloudflare, and other bot-detection systems.
- **Adaptive Parsing:** Ability to find elements based on patterns rather than strict paths.
- **JavaScript Rendering:** Full support for Single Page Applications (SPAs) via headless browser integration.
- **Session Management:** Supports `user_data_dir` to persist cookies, local storage, and session states.
- **Wait Logic:** Built-in support for `networkidle` and custom timeouts to ensure JS-heavy content is fully loaded.

---

## 5. Fetcher Types
The choice of fetcher determines the performance vs. capability trade-off.

| Fetcher | Mechanism | Use Case | Limitations |
| :--- | :--- | :--- | :--- |
| `StaticFetcher` | HTTP Requests | Fast scraping of static HTML. | Cannot execute JavaScript. |
| `PlaywrightFetcher` | Headless Browser | Sites requiring JS rendering. | Slower, higher resource usage. |
| `StealthyFetcher` | Browser + Stealth | Sites with aggressive anti-bot (403s, CAPTCHAs). | Highest resource usage. |

**AI Instruction:** Always start with `StaticFetcher`. If the response is empty or 403, upgrade to `PlaywrightFetcher`. If still blocked or encountering CAPTCHAs, use `StealthyFetcher`.

---

## 6. Practical Usage Examples

### Example 1: Static Scraping (Fastest)
```python
from scrapling.fetchers import StaticFetcher

fetcher = StaticFetcher()
response = fetcher.fetch("https://example.com")
print(response.html)
```

### Example 2: Dynamic JS Scraping
```python
from scrapling.fetchers import PlaywrightFetcher

fetcher = PlaywrightFetcher()
# wait_until='networkidle' ensures JS is executed
response = fetcher.fetch("https://example.com/dynamic", wait_until='networkidle')
print(response.html)
```

### Example 3: Bypassing Bot Detection (The "Golden" Path)
```python
from scrapling.fetchers import StealthyFetcher

# user_data_dir persists session to avoid repeated bot checks
fetcher = StealthyFetcher(
    headless=True, 
    user_data_dir="./browser_profile"
)
response = fetcher.fetch("https://fbref.com/...", wait_until='networkidle')
```

### Example 4: Data Extraction (Selector System)
Scrapling's response object allows direct interaction:
```python
# Find an element by CSS selector
element = response.find(".team-name") 
# Get text content
text = element.text 
```

---

## 7. Common Errors & Troubleshooting

| Error/Symptom | Root Cause | Resolution |
| :--- | :--- | :--- |
| **HTTP 403 Forbidden** | Bot detection triggered. | Switch to `StealthyFetcher`. Add `user_data_dir`. Add random `time.sleep()` delays. |
| **Empty HTML/No Data** | Content is rendered via JS. | Switch from `StaticFetcher` to `PlaywrightFetcher` or `StealthyFetcher`. |
| **Timeout Error** | Page takes too long to load. | Increase `timeout` parameter (e.g., `timeout=80000`). Use `wait_until='networkidle'`. |
| **AttributeError: '...object has no attribute 'close'** | Incorrect cleanup. | Use `fetcher._browser.close()` and `fetcher._playwright.stop()` for manual cleanup of internal Playwright objects. |

---

## 8. Limitations & Known Issues
- **Extreme Anti-Bots:** While `StealthyFetcher` is powerful, some "Enterprise" level protections (e.g., Akamai, PerimeterX) may still require residential proxies.
- **Memory Consumption:** `Playwright` and `Stealthy` fetchers launch actual browser instances; running too many concurrently without closing them will cause memory exhaustion.
- **Headless Detection:** Some sites can detect the `headless=True` flag. Setting `headless=False` is often required for the most stubborn sites.

---

## 9. Best Practices
1. **Fetcher Hierarchy:** `Static` $\rightarrow$ `Playwright` $\rightarrow$ `Stealthy`.
2. **Session Persistence:** Always use `user_data_dir` when scraping a single site over multiple sessions to maintain cookies.
3. **Human Emulation:** 
   - Use `random.uniform(2, 5)` between requests.
   - Rotate `User-Agent` headers if using `StaticFetcher`.
4. **Resource Management:** Always ensure the browser is closed using a `try...finally` block or a context manager to prevent zombie browser processes.
5. **Wait Strategies:** Use `wait_until='networkidle'` for tables and dashboards; use `wait_until='domcontentloaded'` for simple text pages.

---

## 10. Glossary of Terms
- **Fetcher:** The component responsible for the network request and page retrieval.
- **Stealth:** A set of techniques (overriding `navigator.webdriver`, masking fingerprints) used to hide the fact that a browser is automated.
- **Adaptive Selector:** A selector that can find an element based on proximity or partial matches rather than a hardcoded DOM path.
- **Network Idle:** A state where no new network requests have been made for at least 500ms, indicating the page is likely fully rendered.
- **Headless:** A browser running without a visible graphical user interface.