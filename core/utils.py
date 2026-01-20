from core.services import InquiryEmailService

def fetch_emails_from_gmail():
    """
    後方互換性のためのラッパー関数。
    新しいInquiryEmailServiceを使用する。
    此のファイルは将来的に削除される可能性があります。
    """
    service = InquiryEmailService()
    return service.execute()
