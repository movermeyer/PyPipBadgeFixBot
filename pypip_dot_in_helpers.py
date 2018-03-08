import re

from urllib.parse import urlparse, parse_qsl

PYPIP_REGEX = re.compile(r"http[s]?://pypip.in/([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?", flags=re.IGNORECASE)  # Based on https://stackoverflow.com/a/6041965


# This is a hack. I want to get additional information out of the call to `subn`
found_download_endpoint = False
found_non_download_endpoint = False

PYPIP_IN_REGEX_TO_SHIELDS_IO = {
    "format": "format",
    "implementation": "implementation",
    "license": "l",
    "py_versions": "pyversions",
    "status": "status",
    "v": "v",
    "version": "v",
    "wheel": "wheel"
}


def pypip_in_to_shields_io(pypip_in_url):
    global found_download_endpoint
    global found_non_download_endpoint
    url_parts = urlparse(pypip_in_url)

    query_data = parse_qsl(url_parts.query, keep_blank_values=True)
    query_data = [("label", x[1]) if x[0] == "text" else x for x in query_data]

    endpoint = url_parts.path.split('/')[1]
    project = url_parts.path.split('/')[2]
    shields_path = PYPIP_IN_REGEX_TO_SHIELDS_IO.get(endpoint)

    if endpoint in ["d", "download"]:
        found_download_endpoint = True
        period = [x[1] for x in query_data if x[0] == "period"]
        query_data = [x for x in query_data if x[0] != "period"]
        if len(period) > 0:
            period = period[0]
            if period == "day":
                shields_path = "dd"
            elif period == "week":
                shields_path = "dw"
            elif period == "month":
                shields_path = "dm"
            else:
                shields_path = "dm"
        else:
            shields_path = "dm"
    else:
        found_non_download_endpoint = True

    query_data = ["=".join(x) for x in query_data]
    query = "&".join(query_data)

    return None if shields_path is None else f"https://img.shields.io/pypi/{shields_path}/{project}.svg{'?' if query else ''}{query}"


def generate_shields_io_url_from_pypip_url(match):
    badge_image_url = match.group(0)
    new_badge_url = pypip_in_to_shields_io(badge_image_url)
    return new_badge_url if new_badge_url is not None else badge_image_url


def replace_in_readme(readme):
    global found_download_endpoint
    global found_non_download_endpoint
    found_download_endpoint = False
    found_non_download_endpoint = False
    new_readme, n = PYPIP_REGEX.subn(generate_shields_io_url_from_pypip_url, readme)
    return new_readme, n, found_download_endpoint, found_non_download_endpoint
