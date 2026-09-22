from pathlib import Path
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import random
import time
import importlib
import subprocess
import sys


# =========================================================
# 第三方套件自動檢查 / 安裝
# =========================================================

REQUIRED_PACKAGES = {
    "yaml": "PyYAML",
    "playwright": "playwright",
}


def ensure_required_packages():
    """
    檢查目前 Python 環境是否已安裝必要套件。

    若缺少套件：
        自動使用目前執行中的 Python：
        python -m pip install <package>
    """

    missing_packages = []

    for import_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing_packages.append(pip_name)

    if not missing_packages:
        print("必要 Python 套件已安裝完成")
        return

    print(
        "偵測到缺少 Python 套件："
        + ", ".join(missing_packages)
    )

    for pip_name in missing_packages:
        print(f"開始安裝：{pip_name}")

        try:
            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    pip_name
                ]
            )

        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"自動安裝 {pip_name} 失敗，"
                f"請手動執行："
                f"{sys.executable} -m pip install {pip_name}"
            ) from e

        print(f"安裝完成：{pip_name}")

    for import_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(import_name)
        except ImportError as e:
            raise RuntimeError(
                f"套件 {pip_name} 安裝後仍無法 import。"
            ) from e

    print("所有必要 Python 套件準備完成")


ensure_required_packages()


import yaml

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
)


# =========================================================
# 基本設定
# =========================================================

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"

DEFAULT_CONFIG = {
    "log_max_jobs": 500,
    "max_jobs": 500,
    "max_pages": 50,
}


def load_config():
    """
    讀取目前程式目錄下的 config.yaml。

    支援設定：
        log_max_jobs
        max_jobs
        max_pages
    """

    config = DEFAULT_CONFIG.copy()

    if not CONFIG_PATH.exists():
        print(f"找不到設定檔：{CONFIG_PATH.name}")
        print(
            "使用預設設定："
            f"LOG_MAX_JOBS={config['log_max_jobs']}、"
            f"MAX_JOBS={config['max_jobs']}、"
            f"MAX_PAGES={config['max_pages']}"
        )
        return config

    try:
        with open(
                CONFIG_PATH,
                "r",
                encoding="utf-8"
        ) as file:
            loaded = yaml.safe_load(file)

    except Exception as e:
        print(
            f"讀取設定檔失敗："
            f"{type(e).__name__}: {e}"
        )
        print("改用預設設定。")
        return config

    if loaded is None:
        loaded = {}

    if not isinstance(loaded, dict):
        print(
            "設定檔格式錯誤："
            "config.yaml 最外層必須是 YAML mapping。"
        )
        print("改用預設設定。")
        return config

    for key, default_value in DEFAULT_CONFIG.items():
        value = loaded.get(
            key,
            default_value
        )

        if (
                isinstance(value, int)
                and not isinstance(value, bool)
                and value > 0
        ):
            config[key] = value
        else:
            print(
                f"設定 {key}={value!r} 不合法，"
                f"改用預設值 {default_value}"
            )

    print(f"已讀取設定檔：{CONFIG_PATH}")
    print(
        "目前設定："
        f"LOG_MAX_JOBS={config['log_max_jobs']}、"
        f"MAX_JOBS={config['max_jobs']}、"
        f"MAX_PAGES={config['max_pages']}"
    )

    return config


CONFIG = load_config()

LOG_MAX_JOBS = CONFIG["log_max_jobs"]
MAX_JOBS = CONFIG["max_jobs"]
MAX_PAGES = CONFIG["max_pages"]

MEMORY_CLEANUP_INTERVAL = 20

# 開啟後會印出背景 / 前景、readyState、DOM 長度等資訊。
DEBUG_PAGE_STATE = True

BLOCKED_RESOURCE_URLS = [
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.webp",
    "*.svg",
    "*.ico",
    "*.mp4",
    "*.webm",
    "*.avi",
    "*.mov",
    "*.woff",
    "*.woff2",
    "*.ttf",
    "*.otf",
]

CDP_URL = "http://127.0.0.1:9333"

LOG_DIR = SCRIPT_DIR / "log"

CARD_SELECTORS = [
    "div.job-summary[data-job-no]",
    "div.job-mobile[data-job-no]",
]

LINK_SELECTORS = [
    "a.info-job__text",
    "a.info-job",
    "a.js-job-link",
]


# =========================================================
# LOG
# =========================================================

def ensure_log_directory():
    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print(f"LOG 資料夾：{LOG_DIR}")


def create_log_file():
    while True:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        log_path = (
                LOG_DIR
                / f"OOF_{timestamp}.log"
        )

        if not log_path.exists():
            break

        time.sleep(1)

    log_path.touch(
        exist_ok=False
    )

    print(
        f"建立新的 LOG：{log_path.name}"
    )

    return log_path


def write_log(
        log_path,
        message=""
):
    with open(
            log_path,
            "a",
            encoding="utf-8"
    ) as file:
        file.write(
            message + "\n"
        )


def write_job_log(
        log_path,
        job_no,
        job_name,
        location,
        technologies,
        education,
        salary,
        href
):
    separator = "=" * 100

    lines = [
        separator,
        f"職缺編號：{job_no}",
        f"職缺名稱：{job_name}",
        f"工作地點：{location}",
        f"需要技術：{technologies}",
        f"學歷限制：{education}",
        f"薪資範圍：{salary}",
        f"職缺網址：{href}",
        separator,
        ""
    ]

    with open(
            log_path,
            "a",
            encoding="utf-8"
    ) as file:
        for line in lines:
            file.write(
                line + "\n"
            )


# =========================================================
# Playwright / Chrome
# =========================================================

def attach_to_existing_chrome(playwright):
    """
    連線到已經手動啟動，且開啟 remote debugging 的 Chrome。
    """

    browser = playwright.chromium.connect_over_cdp(
        CDP_URL
    )

    if not browser.contexts:
        raise RuntimeError(
            "已連線 Chrome，但沒有找到 BrowserContext。"
        )

    context = browser.contexts[0]

    return browser, context


def get_current_page(context):
    """
    取得目前 Chrome 中要交給程式使用的分頁。

    優先找目前有焦點的頁面。
    如果 Chrome 不在前景，document.hasFocus() 可能全部為 False，
    此時退回使用 context.pages[-1]。
    """

    pages = context.pages

    if not pages:
        raise RuntimeError(
            "目前 Chrome 沒有任何可用分頁。"
        )

    focused_page = None

    for page in pages:
        try:
            if page.evaluate("() => document.hasFocus()"):
                focused_page = page
                break
        except Exception:
            continue

    page = focused_page or pages[-1]

    print()
    print("=" * 100)
    print("使用目前 Chrome 分頁")
    print(f"頁面標題：{page.title()}")
    print(f"頁面網址：{page.url}")

    if focused_page is None:
        print(
            "目前沒有偵測到有焦點的分頁，"
            "改用 Chrome Context 中最後一個分頁。"
        )

    print("=" * 100)
    print()

    return page


def create_low_memory_cdp_session(context, page):
    """
    為指定 Page 建立 CDP Session，並套用低記憶體設定。
    """

    session = context.new_cdp_session(page)

    try:
        session.send("Network.enable")
    except Exception:
        pass

    try:
        session.send(
            "Network.setCacheDisabled",
            {
                "cacheDisabled": True
            }
        )
    except Exception as e:
        print(
            f"設定停用 Cache 失敗："
            f"{type(e).__name__}: {e}"
        )

    try:
        session.send(
            "Network.setBlockedURLs",
            {
                "urls": BLOCKED_RESOURCE_URLS
            }
        )
    except Exception as e:
        print(
            f"設定資源阻擋失敗："
            f"{type(e).__name__}: {e}"
        )

    return session


def cleanup_chrome_memory(session):
    """
    在不開新 Tab、不切換視窗的情況下，
    要求 Chrome 清理 Browser Cache 與 JavaScript Heap。
    """

    print("  執行 Chrome 記憶體清理...")

    try:
        session.send(
            "Network.clearBrowserCache"
        )
    except Exception:
        pass

    try:
        session.send(
            "HeapProfiler.collectGarbage"
        )
    except Exception:
        pass

    try:
        session.send(
            "Memory.forciblyPurgeJavaScriptMemory"
        )
    except Exception:
        pass


def print_page_state(page):
    """
    印出目前頁面的可見狀態與 DOM 狀態，
    用來確認背景分頁是否影響內容載入。
    """

    if not DEBUG_PAGE_STATE:
        return

    try:
        state = page.evaluate(
            """
            () => ({
                hasFocus: document.hasFocus(),
                hidden: document.hidden,
                visibilityState: document.visibilityState,
                readyState: document.readyState,
                bodyTextLength: document.body?.textContent?.length ?? 0,
                bodyHtmlLength: document.body?.innerHTML?.length ?? 0
            })
            """
        )

        print(
            "  Page 狀態："
            f"focus={state['hasFocus']}、"
            f"hidden={state['hidden']}、"
            f"visibility={state['visibilityState']}、"
            f"readyState={state['readyState']}、"
            f"textLength={state['bodyTextLength']}、"
            f"htmlLength={state['bodyHtmlLength']}"
        )

    except Exception as e:
        print(
            f"  無法取得 Page 狀態："
            f"{type(e).__name__}: {e}"
        )


def wait_for_job_detail(
        page,
        timeout=15000
):
    """
    等待職缺詳細資料真正出現在 DOM。

    重點：
    - 不依賴固定 sleep
    - 不要求 visible，只要求 DOM 裡已存在內容
    - 避免背景分頁 rendering / timer throttling 造成過早擷取

    判斷條件：
    工作待遇 / 上班地點 / 學歷要求
    至少找到 2 個才視為主要詳細資料已載入。
    """

    labels = [
        "工作待遇",
        "上班地點",
        "學歷要求",
    ]

    deadline = time.monotonic() + (timeout / 1000)
    found_labels = set()

    while time.monotonic() < deadline:
        for label in labels:
            if label in found_labels:
                continue

            try:
                count = page.get_by_text(
                    label,
                    exact=True
                ).count()

                if count > 0:
                    found_labels.add(label)

            except Exception:
                pass

        if len(found_labels) >= 2:
            print(
                "  職缺詳細資料已進入 DOM："
                + "、".join(sorted(found_labels))
            )
            return True

        time.sleep(0.2)

    print(
        "  警告：等待職缺詳細資料逾時，"
        f"目前找到：{sorted(found_labels)}"
    )

    return False


def navigate_job_page(
        page,
        url,
        timeout=30000
):
    """
    導航到職缺詳細頁，並分階段等待：

    1. DOMContentLoaded
    2. document.readyState == complete
    3. networkidle（非必要，等不到不視為失敗）
    4. 等待職缺主要欄位進入 DOM

    對 Vue / JavaScript 動態頁比固定 sleep 穩定。
    """

    try:
        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=timeout
        )

    except PlaywrightTimeoutError:
        print(
            "  DOMContentLoaded 等待逾時，"
            "繼續嘗試等待目前頁面"
        )

    try:
        page.wait_for_function(
            "() => document.readyState === 'complete'",
            timeout=timeout
        )

    except PlaywrightTimeoutError:
        print(
            "  document.readyState 等待逾時，"
            "繼續處理"
        )

    try:
        page.wait_for_load_state(
            "networkidle",
            timeout=8000
        )

    except PlaywrightTimeoutError:
        print(
            "  networkidle 未達成，"
            "可能仍有 analytics / tracking request，"
            "繼續等待職缺內容"
        )

    wait_for_job_detail(
        page,
        timeout=15000
    )

    print_page_state(
        page
    )


# =========================================================
# URL / 分頁
# =========================================================

def get_page_number(url):
    """
    取得 URL 中的 page 參數。
    沒有時視為第 1 頁。
    """

    parts = urlsplit(url)

    query = dict(
        parse_qsl(
            parts.query,
            keep_blank_values=True
        )
    )

    try:
        return int(
            query.get(
                "page",
                "1"
            )
        )
    except ValueError:
        return 1


def set_page_number(
        url,
        page_number
):
    """
    保留原本搜尋條件，只修改 page 參數。
    """

    parts = urlsplit(url)

    query_pairs = parse_qsl(
        parts.query,
        keep_blank_values=True
    )

    new_pairs = []
    page_replaced = False

    for key, value in query_pairs:
        if key == "page":
            new_pairs.append(
                (
                    "page",
                    str(page_number)
                )
            )
            page_replaced = True
        else:
            new_pairs.append(
                (
                    key,
                    value
                )
            )

    if not page_replaced:
        new_pairs.append(
            (
                "page",
                str(page_number)
            )
        )

    new_query = urlencode(
        new_pairs,
        doseq=True
    )

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            new_query,
            parts.fragment
        )
    )


# =========================================================
# 職缺列表
# =========================================================

def wait_for_job_cards(
        page,
        timeout=10000
):
    """
    等待至少一種職缺卡片出現。
    """

    for selector in CARD_SELECTORS:
        try:
            page.locator(
                selector
            ).first.wait_for(
                state="attached",
                timeout=timeout
            )

            return selector

        except PlaywrightTimeoutError:
            continue

    return None


def extract_jobs_from_current_page(page):
    """
    一次用 JavaScript 從 DOM 把：
    job_no
    href
    全部取回來。
    """

    result = page.evaluate(
        """
        ({ cardSelectors, linkSelectors }) => {

            let cards = [];

            for (const selector of cardSelectors) {

                const found = Array.from(
                    document.querySelectorAll(selector)
                );

                if (found.length > 0) {
                    cards = found;
                    break;
                }
            }

            return cards.map(card => {

                const jobNo = card.getAttribute(
                    'data-job-no'
                );

                let link = null;

                for (const selector of linkSelectors) {

                    link = card.querySelector(
                        selector
                    );

                    if (link) {
                        break;
                    }
                }

                return {
                    jobNo: jobNo,
                    href: link ? link.href : null
                };
            });
        }
        """,
        {
            "cardSelectors": CARD_SELECTORS,
            "linkSelectors": LINK_SELECTORS
        }
    )

    jobs = []

    for item in result:
        job_no = item.get(
            "jobNo"
        )

        href = item.get(
            "href"
        )

        if not job_no:
            continue

        if not href:
            continue

        jobs.append(
            (
                str(job_no),
                href
            )
        )

    return jobs


def collect_job_links(
        page,
        max_jobs=MAX_JOBS,
        max_pages=MAX_PAGES
):
    """
    用網站本身的 page= 分頁收集職缺。
    """

    print(
        "目前頁面網址：",
        page.url
    )

    print(
        "目前頁面標題：",
        page.title()
    )

    base_url = page.url

    start_page = get_page_number(
        base_url
    )

    print(
        f"從第 {start_page} 頁開始收集"
    )

    print("=" * 100)

    seen = {}

    empty_or_duplicate_pages = 0

    for offset in range(
            max_pages
    ):
        if len(seen) >= max_jobs:
            break

        current_page_number = (
                start_page
                + offset
        )

        target_url = set_page_number(
            base_url,
            current_page_number
        )

        print()

        print(
            f"[Page {current_page_number}] "
            f"目前已收集 "
            f"{len(seen)}/{max_jobs} 筆"
        )

        if page.url != target_url:
            try:
                page.goto(
                    target_url,
                    wait_until="domcontentloaded",
                    timeout=30000
                )

            except PlaywrightTimeoutError:
                print(
                    "  頁面導航逾時，"
                    "但繼續檢查目前 DOM"
                )

        selector = wait_for_job_cards(
            page,
            timeout=10000
        )

        if selector is None:
            print(
                "  找不到職缺卡片"
            )

            empty_or_duplicate_pages += 1

            if empty_or_duplicate_pages >= 3:
                print(
                    "  連續 3 頁沒有有效職缺，停止收集。"
                )
                break

            continue

        print(
            f"  使用卡片選擇器：{selector}"
        )

        time.sleep(
            random.uniform(
                0.8,
                1.5
            )
        )

        jobs = extract_jobs_from_current_page(
            page
        )

        print(
            f"  此頁找到 {len(jobs)} 張職缺卡片"
        )

        count_before = len(
            seen
        )

        for job_no, href in jobs:
            if job_no in seen:
                continue

            seen[job_no] = href

            if len(seen) >= max_jobs:
                break

        new_count = (
                len(seen)
                - count_before
        )

        print(
            f"  本頁新增 {new_count} 筆"
        )

        print(
            f"  目前總數："
            f"{len(seen)}/{max_jobs}"
        )

        if new_count == 0:
            empty_or_duplicate_pages += 1

            print(
                f"  本頁沒有新職缺 "
                f"({empty_or_duplicate_pages}/3)"
            )
        else:
            empty_or_duplicate_pages = 0

        if empty_or_duplicate_pages >= 3:
            print(
                "  連續 3 頁沒有新增職缺，停止收集。"
            )
            break

        if len(seen) < max_jobs:
            delay = random.uniform(
                1.2,
                2.5
            )

            print(
                f"  前往下一頁前等待 "
                f"{delay:.1f} 秒"
            )

            time.sleep(
                delay
            )

    if len(seen) > max_jobs:
        seen = dict(
            list(
                seen.items()
            )[:max_jobs]
        )

    print()
    print("=" * 100)

    print(
        f"職缺連結收集完成，"
        f"總共 {len(seen)} 筆"
    )

    print("=" * 100)

    return seen


# =========================================================
# 通用文字處理
# =========================================================

def clean_text(text):
    if text is None:
        return ""

    return " ".join(
        text.split()
    ).strip()


def safe_get_text(
        page,
        selectors
):
    """
    依序嘗試多個 CSS selector，
    找到第一個有文字的元素就回傳。

    使用 text_content()，
    避免依賴實際畫面 rendering。
    """

    for selector in selectors:
        try:
            locator = page.locator(
                selector
            )

            count = locator.count()

            for index in range(
                    count
            ):
                text = clean_text(
                    locator.nth(
                        index
                    ).text_content(
                        timeout=5000
                    )
                )

                if text:
                    return text

        except Exception as e:
            if DEBUG_PAGE_STATE:
                print(
                    f"  safe_get_text 失敗："
                    f"selector={selector}、"
                    f"{type(e).__name__}: {e}"
                )

            continue

    return None


def extract_row_value(
        page,
        labels
):
    """
    優先直接從 求職網 詳細頁的 list-row 結構取得欄位。

    結構大致為：
        .list-row
            h3 = 欄位名稱
            .list-row__data = 欄位內容

    如果 DOM 改版或找不到，回傳 None，
    讓上層 fallback 到全文文字解析。
    """

    for label in labels:
        try:
            rows = page.locator(
                ".list-row"
            )

            count = rows.count()

            for index in range(count):
                row = rows.nth(index)

                head = row.locator(
                    "h3"
                ).first

                if head.count() == 0:
                    continue

                head_text = clean_text(
                    head.text_content(
                        timeout=2000
                    )
                )

                if head_text != label:
                    continue

                data = row.locator(
                    ".list-row__data"
                ).first

                if data.count() == 0:
                    continue

                value = clean_text(
                    data.text_content(
                        timeout=3000
                    )
                )

                if value:
                    return value

        except Exception as e:
            if DEBUG_PAGE_STATE:
                print(
                    f"  extract_row_value 失敗："
                    f"label={label}、"
                    f"{type(e).__name__}: {e}"
                )

    return None


# =========================================================
# 詳細頁文字解析
# =========================================================

def get_page_lines(page):
    """
    取得整個 body 的文字。

    使用 text_content()，不使用 inner_text()，
    避免背景分頁與 rendering 狀態影響。
    """

    try:
        text = page.locator(
            "body"
        ).text_content(
            timeout=10000
        )

        if not text:
            return []

        lines = []

        for line in text.splitlines():
            line = clean_text(
                line
            )

            if line:
                lines.append(
                    line
                )

        return lines

    except Exception as e:
        print(
            f"  取得頁面文字失敗："
            f"{type(e).__name__}: {e}"
        )

        return []


def extract_value_after_label(
        lines,
        labels,
        max_lookahead=3
):
    for index, line in enumerate(
            lines
    ):
        for label in labels:
            if line.startswith(
                    label + "："
            ):
                value = clean_text(
                    line[
                        len(label) + 1:
                    ]
                )

                if value:
                    return value

            if line == label:
                for offset in range(
                        1,
                        max_lookahead + 1
                ):
                    next_index = (
                            index
                            + offset
                    )

                    if next_index >= len(
                            lines
                    ):
                        break

                    value = clean_text(
                        lines[
                            next_index
                        ]
                    )

                    if value:
                        return value

    return None


def extract_multi_value_after_label(
        lines,
        labels,
        max_lines=3
):
    stop_labels = {
        "工作技能",
        "其他條件",
        "具備駕照",
        "具備證照",
        "歡迎身分",
        "公司福利",
        "聯絡方式",
        "工作經歷",
        "學歷要求",
        "科系要求",
        "語文條件",
        "上班時段",
        "休假制度",
        "可上班日",
        "需求人數",
        "工作地點",
        "上班地點",
        "工作待遇",
        "職務類別"
    }

    for index, line in enumerate(
            lines
    ):
        for label in labels:
            if line.startswith(
                    label + "："
            ):
                value = clean_text(
                    line[
                        len(label) + 1:
                    ]
                )

                if value:
                    return value

            if line == label:
                values = []

                for offset in range(
                        1,
                        max_lines + 1
                ):
                    next_index = (
                            index
                            + offset
                    )

                    if next_index >= len(
                            lines
                    ):
                        break

                    value = clean_text(
                        lines[
                            next_index
                        ]
                    )

                    if not value:
                        continue

                    if value in stop_labels:
                        break

                    values.append(
                        value
                    )

                if values:
                    return "、".join(
                        values
                    )

    return None


def extract_job_name(
        page,
        lines
):
    selectors = [
        "h1",
        "h1[class*='job']",
        "[data-qa='job-title']",
    ]

    value = safe_get_text(
        page,
        selectors
    )

    if value:
        return value

    title = page.title()

    if title:
        if "｜" in title:
            title = title.split(
                "｜"
            )[0]

        return clean_text(
            title
        )

    return "未取得"


def extract_job_location(
        page,
        lines
):
    value = extract_row_value(
        page,
        [
            "上班地點",
            "工作地點"
        ]
    )

    if value:
        return value

    value = extract_value_after_label(
        lines,
        [
            "工作地點",
            "上班地點"
        ]
    )

    return value or "未取得"


def extract_education(
        page,
        lines
):
    value = extract_row_value(
        page,
        [
            "學歷要求",
            "學歷"
        ]
    )

    if value:
        return value

    value = extract_value_after_label(
        lines,
        [
            "學歷要求",
            "學歷"
        ]
    )

    return value or "未取得"


def extract_salary(
        page,
        lines
):
    value = extract_row_value(
        page,
        [
            "工作待遇",
            "薪資待遇",
            "薪資"
        ]
    )

    if value:
        return value

    value = extract_value_after_label(
        lines,
        [
            "工作待遇",
            "薪資待遇",
            "薪資"
        ]
    )

    return value or "未取得"


def extract_technologies(
        page,
        lines
):
    technologies = []

    # 先嘗試 DOM row。
    tools = extract_row_value(
        page,
        [
            "擅長工具",
            "電腦專長"
        ]
    )

    if not tools:
        tools = extract_multi_value_after_label(
            lines,
            [
                "擅長工具",
                "電腦專長"
            ],
            max_lines=5
        )

    if tools:
        technologies.append(
            tools
        )

    skills = extract_row_value(
        page,
        [
            "工作技能"
        ]
    )

    if not skills:
        skills = extract_multi_value_after_label(
            lines,
            [
                "工作技能"
            ],
            max_lines=5
        )

    if skills:
        technologies.append(
            skills
        )

    if technologies:
        unique_values = []

        for value in technologies:
            if value not in unique_values:
                unique_values.append(
                    value
                )

        return "、".join(
            unique_values
        )

    return "未取得"


def extract_job_detail(page):
    lines = get_page_lines(
        page
    )

    return {
        "job_name": extract_job_name(
            page,
            lines
        ),
        "location": extract_job_location(
            page,
            lines
        ),
        "technologies": extract_technologies(
            page,
            lines
        ),
        "education": extract_education(
            page,
            lines
        ),
        "salary": extract_salary(
            page,
            lines
        ),
    }


def count_missing_detail_fields(detail):
    """
    job_name 不計入缺少欄位判斷。
    """

    keys = [
        "location",
        "technologies",
        "education",
        "salary",
    ]

    return sum(
        1
        for key in keys
        if not detail.get(key)
        or detail.get(key) == "未取得"
    )


def extract_job_detail_with_retry(
        page,
        retry_count=2
):
    """
    取得職缺資料。

    若 location / technologies / education / salary
    有 3 個以上未取得，代表很可能抓太早，
    重新等待 DOM 後再次解析。
    """

    for attempt in range(
            retry_count + 1
    ):
        detail = extract_job_detail(
            page
        )

        missing_count = count_missing_detail_fields(
            detail
        )

        if missing_count < 3:
            return detail

        if attempt >= retry_count:
            return detail

        print(
            f"  詳細資料不足 "
            f"({missing_count}/4 未取得)，"
            f"第 {attempt + 1} 次重新等待後再讀取..."
        )

        print_page_state(
            page
        )

        wait_for_job_detail(
            page,
            timeout=8000
        )

        time.sleep(
            0.3
        )

    return detail


# =========================================================
# 模擬閱讀
# =========================================================

def simulate_reading(
        page,
        total_duration_range=(10, 30)
):
    total_duration = random.uniform(
        *total_duration_range
    )

    elapsed = 0

    initial_pause = random.uniform(
        1,
        2
    )

    time.sleep(
        initial_pause
    )

    elapsed += (
        initial_pause
    )

    print(
        f"  預計閱讀："
        f"{total_duration:.1f} 秒"
    )

    while elapsed < total_duration:
        action = random.choices(
            [
                "scroll_down",
                "scroll_down_small",
                "scroll_up",
                "pause"
            ],
            weights=[
                45,
                30,
                10,
                15
            ]
        )[0]

        if action == "scroll_down":
            distance = random.randint(
                300,
                600
            )

            page.evaluate(
                "(distance) => window.scrollBy(0, distance)",
                distance
            )

        elif action == "scroll_down_small":
            distance = random.randint(
                100,
                250
            )

            page.evaluate(
                "(distance) => window.scrollBy(0, distance)",
                distance
            )

        elif action == "scroll_up":
            distance = random.randint(
                100,
                300
            )

            page.evaluate(
                "(distance) => window.scrollBy(0, -distance)",
                distance
            )

        step_pause = random.uniform(
            1.2,
            3.5
        )

        time.sleep(
            step_pause
        )

        elapsed += (
            step_pause
        )


# =========================================================
# 逐筆瀏覽職缺
# =========================================================

def visit_jobs(
        page,
        job_links,
        cdp_session,
        view_duration_range=(10, 30),
        batch_size_range=(10, 15),
        long_break_range=(30, 60),
        memory_cleanup_interval=MEMORY_CLEANUP_INTERVAL
):
    next_batch_target = random.randint(
        *batch_size_range
    )

    count_since_break = 0

    total_jobs = len(
        job_links
    )

    jobs_in_current_log = 0

    current_log = create_log_file()

    print()
    print("=" * 100)
    print("職缺連結已全部收集完成。")
    print(
        "接下來使用同一個 Chrome Tab 依序瀏覽，"
        "並定期清理 Chrome 記憶體。"
    )
    print("=" * 100)

    for idx, (
            job_no,
            href
    ) in enumerate(
        job_links.items(),
        1
    ):
        if jobs_in_current_log >= LOG_MAX_JOBS:
            print()
            print("=" * 100)

            print(
                f"目前 LOG 已達 {LOG_MAX_JOBS} 筆，"
                "建立新的 LOG"
            )

            print("=" * 100)

            current_log = (
                create_log_file()
            )

            jobs_in_current_log = 0

        print()
        print("=" * 100)

        print(
            f"[{idx}/{total_jobs}] "
            f"瀏覽職缺：{job_no}"
        )

        print(
            f"URL：{href}"
        )

        try:
            print(
                "  等待頁面與職缺詳細資料載入..."
            )

            navigate_job_page(
                page,
                href,
                timeout=30000
            )

            try:
                page.evaluate(
                    "() => window.scrollTo(0, 0)"
                )
            except Exception:
                pass

            # 非主要等待機制，只留極短緩衝給 Vue DOM update。
            time.sleep(
                0.3
            )

            detail = extract_job_detail_with_retry(
                page,
                retry_count=2
            )

            job_name = detail[
                "job_name"
            ]

            location = detail[
                "location"
            ]

            technologies = detail[
                "technologies"
            ]

            education = detail[
                "education"
            ]

            salary = detail[
                "salary"
            ]

            print(
                f"職缺名稱："
                f"{job_name}"
            )

            print(
                f"工作地點："
                f"{location}"
            )

            print(
                f"需要技術："
                f"{technologies}"
            )

            print(
                f"學歷限制："
                f"{education}"
            )

            print(
                f"薪資範圍："
                f"{salary}"
            )

            print("=" * 100)

            write_job_log(
                current_log,
                job_no=job_no,
                job_name=job_name,
                location=location,
                technologies=technologies,
                education=education,
                salary=salary,
                href=href
            )

            jobs_in_current_log += 1

            print(
                f"  已寫入 LOG："
                f"{current_log.name}"
            )

            print(
                f"  此 LOG 已有 "
                f"{jobs_in_current_log}/"
                f"{LOG_MAX_JOBS} 筆"
            )

            simulate_reading(
                page,
                view_duration_range
            )

            print(
                "  瀏覽完成"
            )

        except Exception as e:
            print(
                f"  瀏覽失敗："
                f"{type(e).__name__}: "
                f"{e}"
            )

            write_log(
                current_log,
                "=" * 100
            )

            write_log(
                current_log,
                f"職缺編號：{job_no}"
            )

            write_log(
                current_log,
                f"職缺網址：{href}"
            )

            write_log(
                current_log,
                "狀態：讀取失敗"
            )

            write_log(
                current_log,
                (
                    f"錯誤："
                    f"{type(e).__name__}: "
                    f"{e}"
                )
            )

            write_log(
                current_log,
                "=" * 100
            )

            write_log(
                current_log
            )

            jobs_in_current_log += 1

        if (
                memory_cleanup_interval > 0
                and idx % memory_cleanup_interval == 0
        ):
            cleanup_chrome_memory(
                cdp_session
            )

        count_since_break += 1

        if idx < total_jobs:
            short_break = random.uniform(
                2,
                5
            )

            print(
                f"下一筆前等待："
                f"{short_break:.1f} 秒"
            )

            time.sleep(
                short_break
            )

        if (
                count_since_break
                >= next_batch_target
                and idx < total_jobs
        ):
            break_duration = random.uniform(
                *long_break_range
            )

            print()

            print(
                f"已連續瀏覽 "
                f"{count_since_break} 筆"
            )

            print(
                f"休息中..."
                f"約 {break_duration:.0f} 秒"
            )

            time.sleep(
                break_duration
            )

            count_since_break = 0

            next_batch_target = (
                random.randint(
                    *batch_size_range
                )
            )


# =========================================================
# MAIN
# =========================================================

def main():
    print("=" * 100)
    print("OOF Playwright 自動職缺瀏覽程式")
    print("=" * 100)
    print()

    print(
        "檢查 LOG 資料夾..."
    )

    ensure_log_directory()

    print(
        "LOG 資料夾確認完成"
    )

    print()

    print(
        "連接 Chrome..."
    )

    with sync_playwright() as playwright:
        browser, context = (
            attach_to_existing_chrome(
                playwright
            )
        )

        print(
            "Chrome 連接成功"
        )

        page = get_current_page(
            context
        )

        list_cdp_session = create_low_memory_cdp_session(
            context,
            page
        )

        print(
            "開始收集職缺連結..."
        )

        job_links = collect_job_links(
            page,
            max_jobs=MAX_JOBS,
            max_pages=MAX_PAGES
        )

        print()

        print(
            f"共收集到 "
            f"{len(job_links)} 筆職缺"
        )

        if len(job_links) == 0:
            print()
            print(
                "沒有收集到任何職缺。"
            )

            print(
                "請確認："
            )

            print(
                "1. 是否停留在求職網搜尋列表"
            )

            print(
                "2. Cloudflare 是否已通過"
            )

            print(
                "3. 求職網 DOM 是否改版"
            )

            return

        print()
        print("=" * 100)
        print("職缺連結收集完成")
        print("準備切換到新的瀏覽分頁...")
        print("=" * 100)

        job_list_page = page

        page = context.new_page()

        try:
            page.goto(
                "about:blank",
                wait_until="commit",
                timeout=10000
            )
        except Exception:
            pass

        browse_cdp_session = create_low_memory_cdp_session(
            context,
            page
        )

        try:
            try:
                list_cdp_session.detach()
            except Exception:
                pass

            job_list_page.close()

            print(
                "原職缺列表分頁已關閉"
            )

        except Exception as e:
            print(
                f"關閉原職缺列表分頁失敗："
                f"{type(e).__name__}: "
                f"{e}"
            )

        time.sleep(
            2
        )

        print()
        print(
            "新的瀏覽分頁建立完成"
        )

        print(
            "後續全部職缺都會使用同一個分頁。"
        )

        print(
            "不會再建立新的 Tab。"
        )

        print()

        print(
            "開始逐一瀏覽職缺..."
        )

        visit_jobs(
            page,
            job_links,
            browse_cdp_session,
            view_duration_range=(
                10,
                30
            ),
            batch_size_range=(
                10,
                15
            ),
            long_break_range=(
                30,
                60
            )
        )

        print()
        print("=" * 100)
        print("全部瀏覽完成")

        print(
            f"LOG 位置："
            f"{LOG_DIR}"
        )

        print("=" * 100)


if __name__ == "__main__":
    main()


# =========================================================
# Chrome 啟動方式
# =========================================================
#
# macOS:
#
# /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
#   --remote-debugging-port=9333 \
#   --user-data-dir="$HOME/selenium-chrome-profile" \
#   --disable-features=BackForwardCache
#
#
# Windows PowerShell:
#
# & "C:\Program Files\Google\Chrome\Application\chrome.exe" `
#   --remote-debugging-port=9333 `
#   --user-data-dir="C:\Users\User\selenium-chrome-profile" `
#   --disable-features=BackForwardCache
#
#
# 啟動後：
#
# 1. 手動開求職網搜尋頁
# 2. 手動通過 Cloudflare
# 3. 執行這支 Python
#
