import re


def validate_phone(phone: str) -> bool:
    phone = re.sub(r'\D', '', phone)

    if len(phone) == 11 and phone[0] == '7':
        return True
    elif len(phone) == 11 and phone[0] == '8':
        return True
    elif len(phone) == 10:
        return True
    return False


def validate_area(area_str: str) -> bool:
    try:
        area = float(area_str.replace(',', '.'))
        return 1 <= area <= 1000
    except ValueError:
        return False


def format_phone(phone: str) -> str:
    phone = re.sub(r'\D', '', phone)

    if len(phone) == 11 and phone[0] == '7':
        return f"+7 ({phone[1:4]}) {phone[4:7]}-{phone[7:9]}-{phone[9:11]}"
    elif len(phone) == 11 and phone[0] == '8':
        return f"8 ({phone[1:4]}) {phone[4:7]}-{phone[7:9]}-{phone[9:11]}"
    elif len(phone) == 10:
        return f"+7 ({phone[0:3]}) {phone[3:6]}-{phone[6:8]}-{phone[8:10]}"
    return phone
