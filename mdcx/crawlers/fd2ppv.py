#!/usr/bin/env python3
import time

from lxml import etree

from ..config.manager import manager
from ..models.log_buffer import LogBuffer


def _parse_cookies(cookie_str: str) -> dict[str, str]:
    """将浏览器复制的 Cookie 字符串解析为字典"""
    cookies = {}
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            key, _, value = item.partition("=")
            cookies[key.strip()] = value.strip()
    return cookies


def get_title(html):
    """获取标题 (简介作为标题, 因为番号本身不是有意义的标题)"""
    nodes = html.xpath('//div[@class="work-brief"]/text()')
    return nodes[0].strip() if nodes else ""


def get_cover(html):
    """获取封面图"""
    nodes = html.xpath('//div[@class="work-image-large work-photos hidden"]/text()')
    url = nodes[0].strip() if nodes else ""
    return url if url.startswith("http") else ""


def get_release_date(html):
    """获取发布日期"""
    nodes = html.xpath('//div[@class="work-meta-label" and text()="發佈日期"]/following-sibling::div[@class="work-meta-value"][1]/text()')
    return nodes[0].strip() if nodes else ""


def get_runtime(html):
    """获取片长"""
    nodes = html.xpath('//*[@id="duration"]/text()')
    return nodes[0].strip() if nodes else ""


def get_actor(html):
    """获取演员名"""
    nodes = html.xpath('//div[@class="artist-details"]//h3[@class="artist-name"]/a/text()')
    actors = [a.strip() for a in nodes if a.strip()]
    return ",".join(actors) if actors else ""


def get_actor_photo(html):
    """获取演员头像"""
    photo = {}
    names = html.xpath('//div[@class="artist-details"]//h3[@class="artist-name"]/a/text()')
    imgs = html.xpath('//img[@class="artist-avatar-medium"]/@src')
    for i, name in enumerate(names):
        name = name.strip()
        if not name:
            continue
        img_url = ""
        if i < len(imgs):
            src = imgs[i].strip()
            if src.startswith("http"):
                img_url = src
            elif src.startswith("/"):
                img_url = "https://fd2ppv.cc" + src
        photo[name] = img_url
    return photo


def get_studio(html):
    """获取卖家"""
    nodes = html.xpath('//div[@class="work-meta-label" and text()="賣家"]/following-sibling::div[@class="work-meta-value"][1]/a/text()')
    return nodes[0].strip() if nodes else ""


def get_mosaic(html):
    """获取马赛克状态"""
    nodes = html.xpath('//div[@class="work-meta-label" and text()="馬賽克"]/following-sibling::div[@class="work-meta-value"][1]')
    if nodes:
        text = etree.tostring(nodes[0], method="text", encoding="unicode").strip()
        if "無" in text:
            return "无码"
    return "有码"


def get_outline(html):
    """获取简介"""
    nodes = html.xpath('//div[@class="work-brief"]/text()')
    return nodes[0].strip() if nodes else ""


def is_logged_in(html) -> bool:
    """检测是否已登录: 已登录页面包含 '您好' 文本"""
    logged_nodes = html.xpath('//*[contains(text(), "您好")]')
    return len(logged_nodes) > 0


async def check_cookie_valid() -> tuple[bool, str]:
    """检查 fd2ppv cookie 是否有效"""
    cookie_str = manager.config.fd2ppv
    if not cookie_str:
        return False, "未配置 FD2PPV Cookie"
    cookies = _parse_cookies(cookie_str)
    html_content, error = await manager.computed.async_client.get_text(
        "https://fd2ppv.cc/", cookies=cookies
    )
    if html_content is None:
        return False, f"网络请求错误: {error}"
    html_info = etree.fromstring(html_content, etree.HTMLParser())
    if is_logged_in(html_info):
        return True, "FD2PPV Cookie 有效"
    return False, "FD2PPV Cookie 无效或已过期, 请重新从浏览器复制"


async def main(
    number,
    appoint_url="",
    **kwargs,
):
    start_time = time.time()
    website_name = "fd2ppv"
    LogBuffer.req().write(f"-> {website_name}")
    real_url = appoint_url
    number = number.upper().replace("FC2PPV", "").replace("FC2-PPV-", "").replace("FC2-", "").replace("-", "").strip()
    dic = {}
    web_info = "\n       "

    try:
        cookie_str = manager.config.fd2ppv
        if not cookie_str:
            debug_info = "未配置 FD2PPV Cookie, 跳过"
            LogBuffer.info().write(web_info + debug_info)
            raise Exception(debug_info)
        cookies = _parse_cookies(cookie_str)

        if not real_url:
            real_url = f"https://fd2ppv.cc/articles/{number}"

        debug_info = f"番号地址: {real_url}"
        LogBuffer.info().write(web_info + debug_info)
        # ========================================================================番号详情页
        html_content, error = await manager.computed.async_client.get_text(
            real_url, cookies=cookies
        )
        if html_content is None:
            debug_info = f"网络请求错误: {error}"
            LogBuffer.info().write(web_info + debug_info)
            raise Exception(debug_info)
        html_info = etree.fromstring(html_content, etree.HTMLParser())

        if not is_logged_in(html_info):
            debug_info = "FD2PPV Cookie 无效或已过期"
            LogBuffer.info().write(web_info + debug_info)
            raise Exception(debug_info)

        title = get_title(html_info)
        if not title:
            debug_info = "数据获取失败: 未获取到title！"
            LogBuffer.info().write(web_info + debug_info)
            raise Exception(debug_info)
        cover_url = get_cover(html_info)
        outline = get_outline(html_info)
        release_date = get_release_date(html_info)
        year = release_date[:4] if release_date else ""
        actor = get_actor(html_info)
        actor_photo = get_actor_photo(html_info)
        studio = get_studio(html_info)
        mosaic = get_mosaic(html_info)
        runtime = get_runtime(html_info)

        if "fc2_seller" in manager.config.fields_rule:
            actor = studio

        try:
            dic = {
                "number": "FC2-" + str(number),
                "title": title,
                "originaltitle": title,
                "outline": outline,
                "actor": actor,
                "originalplot": outline,
                "tag": "",
                "release": release_date,
                "year": year,
                "runtime": runtime,
                "score": "",
                "series": "FC2系列",
                "director": "",
                "studio": studio,
                "publisher": studio,
                "source": "fc2",
                "website": real_url,
                "actor_photo": actor_photo if actor_photo else {actor: ""},
                "thumb": cover_url,
                "poster": cover_url,
                "extrafanart": [],
                "trailer": "",
                "image_download": False,
                "image_cut": "center",
                "mosaic": mosaic,
                "wanted": "",
            }
            debug_info = "数据获取成功！"
            LogBuffer.info().write(web_info + debug_info)
        except Exception as e:
            debug_info = f"数据生成出错: {str(e)}"
            LogBuffer.info().write(web_info + debug_info)
            raise Exception(debug_info)

    except Exception as e:
        LogBuffer.error().write(str(e))
        dic = {
            "title": "",
            "thumb": "",
            "website": "",
        }
    dic = {website_name: {"zh_cn": dic, "zh_tw": dic, "jp": dic}}
    LogBuffer.req().write(f"({round(time.time() - start_time)}s) ")
    return dic


if __name__ == "__main__":
    print(main("FC2-4347402"))
