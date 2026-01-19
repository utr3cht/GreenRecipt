import imaplib
import email
from email.header import decode_header
import re
from django.conf import settings
from core.models import Inquiry, InquiryMessage
from django.utils import timezone

def fetch_emails_from_gmail():
    """
    Gmailから未読メールを取得し、InquiryMessageとして取り込むユーティリティ関数。
    戻り値: (success, message)
    """
    # IMAP設定の取得
    IMAP_HOST = getattr(settings, 'EMAIL_IMAP_HOST', None)
    IMAP_USER = getattr(settings, 'EMAIL_IMAP_USER', None)
    IMAP_PASSWORD = getattr(settings, 'EMAIL_IMAP_PASSWORD', None)

    if not (IMAP_HOST and IMAP_USER and IMAP_PASSWORD):
        return False, 'IMAP設定が不足しています。settings.pyを確認してください。'

    try:
        # Gmailに接続
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        # タイムアウト設定などを検討しても良いが、デフォルトでいく
        mail.login(IMAP_USER, IMAP_PASSWORD)
        mail.select("inbox")

        # 未読メールを検索
        status, messages = mail.search(None, '(UNSEEN)')
        if status != "OK":
            return True, "メールボックスの検索に失敗したか、メッセージが見つかりませんでした。"

        email_ids = messages[0].split()
        if not email_ids:
            return True, "新着メールはありませんでした。"

        imported_count = 0
        
        for email_id in email_ids:
            # メールを取得
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # 件名のデコード
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    # Ref IDの解析 ([Ref:123] パターン)
                    match = re.search(r'\[Ref:(\d+)\]', subject)
                    if match:
                        inquiry_id = int(match.group(1))
                        try:
                            inquiry = Inquiry.objects.get(id=inquiry_id)
                            
                            # 本文の取得
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_type = part.get_content_type()
                                    content_disposition = str(part.get("Content-Disposition"))
                                    
                                    if content_type == "text/plain" and "attachment" not in content_disposition:
                                        try:
                                            body = part.get_payload(decode=True).decode()
                                        except:
                                            pass
                                        break
                            else:
                                body = msg.get_payload(decode=True).decode()

                            # 引用部分の削除
                            lines = body.splitlines()
                            cleaned_lines = []
                            for line in lines:
                                stripline = line.strip()
                                # 一般的な引用開始パターン
                                if stripline.startswith("---- 日付：") or \
                                   stripline.startswith("On ") and "wrote:" in stripline or \
                                   stripline.startswith("From:") and "Subject:" in body or \
                                   stripline.startswith("-----Original Message-----") or \
                                   stripline.startswith("________________________________"):
                                    break
                                cleaned_lines.append(line)
                            
                            body = "\n".join(cleaned_lines).strip()

                            # InquiryMessageを作成
                            InquiryMessage.objects.create(
                                inquiry=inquiry,
                                sender_type='user',
                                message=body.strip(),
                                created_at=timezone.now()
                            )
                            
                            # ステータス更新
                            if inquiry.status == 'completed':
                                inquiry.status = 'in_progress'
                                inquiry.save()

                            imported_count += 1

                        except Inquiry.DoesNotExist:
                            pass # 該当するIDがない場合はスキップ

        mail.close()
        mail.logout()
        return True, f"{len(email_ids)} 通の未読メールを確認し、{imported_count} 件の返信を取り込みました。"

    except Exception as e:
        return False, f"メール受信中にエラーが発生しました: {e}"
