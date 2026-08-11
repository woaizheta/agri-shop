"""?????????"""
from pypinyin import lazy_pinyin, Style


def get_pinyin_initials(text: str) -> str:
    """????????????"""
    if not text:
        return ""
    result = []
    for char in text:
        if '一' <= char <= '鿿':
            py = lazy_pinyin(char, style=Style.FIRST_LETTER)
            result.append(py[0].upper() if py else char)
        else:
            result.append(char.upper())
    return ''.join(result)


def search_by_pinyin(db_session, model, field_name: str, keyword: str):
    """??????????????????"""
    # ?????????
    from sqlalchemy import or_
    query = db_session.query(model).filter(
        or_(
            getattr(model, field_name).ilike(f"%{keyword}%"),
            getattr(model, 'barcode', None) == keyword if hasattr(model, 'barcode') else False,
        )
    )
    results = query.all()
    if results:
        return results

    # ???????
    all_records = db_session.query(model).filter(model.is_active == True).all()
    keyword_upper = keyword.upper()
    matched = []
    for record in all_records:
        name = getattr(record, field_name, "")
        initials = get_pinyin_initials(name)
        if keyword_upper in initials:
            matched.append(record)
    return matched
