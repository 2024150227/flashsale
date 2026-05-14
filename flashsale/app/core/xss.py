import html

def escape_html(text: str) -> str:
    """
    对字符串进行HTML转义，防止XSS攻击

    参数:
        text: 需要转义的原始字符串

    返回:
        str: 转义后的安全字符串
    """
    if text is None:
        return ""
    return html.escape(str(text))

def escape_html_fields(data: dict, fields: list) -> dict:
    """
    对字典中指定字段进行HTML转义

    参数:
        data: 原始数据字典
        fields: 需要转义的字段列表

    返回:
        dict: 转义后的数据字典
    """
    result = data.copy()
    for field in fields:
        if field in result:
            result[field] = escape_html(result[field])
    return result