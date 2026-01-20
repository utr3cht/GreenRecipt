import os
import uuid
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from core.models import Inquiry, InquiryMessage
from core.forms import InquiryForm

class InquiryService:
    """
    お問い合わせに関するビジネスロジックを管理するサービスクラス。
    """

    @staticmethod
    def handle_confirm_step(request, form):
        """
        確認画面への遷移準備。画像を一時保存し、テンプレートコンテキストを返す。
        """
        temp_image_name = ""
        if 'image' in request.FILES:
            image_file = request.FILES['image']
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_inquiry')
            os.makedirs(temp_dir, exist_ok=True)
            fs = FileSystemStorage(location=temp_dir)
            ext = os.path.splitext(image_file.name)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            temp_image_name = fs.save(filename, image_file)
        
        return {
            "form": form,
            "temp_image_name": temp_image_name
        }

    @staticmethod
    def create_inquiry(user, form_data, temp_image_name):
        """
        お問い合わせを作成・保存する。
        """
        form = InquiryForm(form_data)
        if not form.is_valid():
            raise ValueError("Invalid form data")

        inquiry = form.save(commit=False)
        if user and user.is_authenticated:
            inquiry.user = user
        
        # 一時画像の処理
        if temp_image_name:
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_inquiry')
            temp_path = os.path.join(temp_dir, temp_image_name)
            if os.path.exists(temp_path):
                with open(temp_path, 'rb') as f:
                    inquiry.image.save(temp_image_name, ContentFile(f.read()), save=False)
                try:
                    os.remove(temp_path)
                except:
                    pass
        
        inquiry.save()
        return inquiry

    @staticmethod
    def reply_to_inquiry(inquiry, subject, message, sender_email=None):
        """
        お問い合わせへの返信を行い、メールを送信する。
        """
        if not sender_email:
            sender_email = settings.DEFAULT_FROM_EMAIL

        subject_with_ref = f"{subject} [Ref:{inquiry.id}]"

        context = {
            'user': inquiry.user if inquiry.user else {'username': 'ゲスト'},
            'subject': subject,
            'message': message,
        }

        text_content = render_to_string('admin/inquiry_reply_email.txt', context)
        html_content = render_to_string('admin/inquiry_reply_email.html', context)

        email = EmailMultiAlternatives(
            subject_with_ref,
            text_content,
            sender_email,
            [inquiry.reply_to_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        # InquiryMessage保存
        InquiryMessage.objects.create(
            inquiry=inquiry,
            sender_type='admin',
            message=message
        )

        # ステータス更新
        if inquiry.status == 'unanswered':
            inquiry.status = 'in_progress'
        
        inquiry.is_replied = True
        inquiry.reply_message = message # 後方互換性
        inquiry.save()

        return True


# --- Email Service ---

import imaplib
import email
from email.header import decode_header
import re

class InquiryEmailService:
    """
    問い合わせメールの取り込みと処理を行うサービスクラス。
    オブジェクト指向設計に基づき、接続、取得、解析、保存の責務を管理する。
    """
    
    def __init__(self):
        self.host = getattr(settings, 'EMAIL_IMAP_HOST', None)
        self.user = getattr(settings, 'EMAIL_IMAP_USER', None)
        self.password = getattr(settings, 'EMAIL_IMAP_PASSWORD', None)
        self.mail = None

    def execute(self):
        """
        メール取り込みのメインフローを実行する。
        Returns:
            tuple: (bool success, str message)
        """
        if not self._validate_settings():
            return False, 'IMAP設定が不足しています。settings.pyを確認してください。'

        try:
            self._connect()
            email_ids = self._fetch_unread_email_ids()
            
            if not email_ids:
                return True, "新着メールはありませんでした。"

            imported_count = self._process_emails(email_ids)
            
            return True, f"{len(email_ids)} 通の未読メールを確認し、{imported_count} 件の返信を取り込みました。"

        except Exception as e:
            return False, f"メール受信中にエラーが発生しました: {e}"
        finally:
            self._disconnect()

    def _validate_settings(self):
        """設定の有効性を検証する"""
        return all([self.host, self.user, self.password])

    def _connect(self):
        """IMAPサーバーへの接続とログインを行う"""
        self.mail = imaplib.IMAP4_SSL(self.host)
        self.mail.login(self.user, self.password)
        self.mail.select("inbox")

    def _disconnect(self):
        """接続を閉じてログアウトする"""
        if self.mail:
            try:
                self.mail.close()
            except:
                pass
            try:
                self.mail.logout()
            except:
                pass

    def _fetch_unread_email_ids(self):
        """未読メールのIDリストを取得する"""
        status, messages = self.mail.search(None, '(UNSEEN)')
        if status != "OK":
            raise Exception("メールボックスの検索に失敗しました。")
        return messages[0].split()

    def _process_emails(self, email_ids):
        """
        複数のメールIDを処理し、取り込み成功数を返す。
        """
        count = 0
        for email_id in email_ids:
            try:
                if self._process_single_email(email_id):
                    count += 1
            except Exception as e:
                # 個別のメール処理エラーはログに出すなどして、全体を止めない
                print(f"Error processing email {email_id}: {e}")
                continue
        return count

    def _process_single_email(self, email_id):
        """
        単一のメールを取得・解析し、該当すればInquiryMessageとして保存する。
        """
        status, msg_data = self.mail.fetch(email_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                return self._handle_message(msg)
        return False

    def _handle_message(self, msg):
        """
        メールメッセージオブジェクトを解析して保存処理を行う。
        """
        subject = self._decode_subject(msg["Subject"])
        inquiry_id = self._extract_ref_id(subject)
        
        if not inquiry_id:
            return False

        try:
            inquiry = Inquiry.objects.get(id=inquiry_id)
            body = self._extract_body(msg)
            cleaned_body = self._strip_quotes(body)
            
            self._save_inquiry_message(inquiry, cleaned_body)
            return True
        except Inquiry.DoesNotExist:
            return False

    def _decode_subject(self, encoded_subject):
        """件名をデコードする"""
        subject, encoding = decode_header(encoded_subject)[0]
        if isinstance(subject, bytes):
            return subject.decode(encoding if encoding else "utf-8")
        return subject

    def _extract_ref_id(self, subject):
        """件名からRef IDを抽出する"""
        match = re.search(r'\[Ref:(\d+)\]', subject)
        if match:
            return int(match.group(1))
        return None

    def _extract_body(self, msg):
        """メール本文を抽出する"""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        return part.get_payload(decode=True).decode()
                    except:
                        pass
        else:
            try:
                return msg.get_payload(decode=True).decode()
            except:
                pass
        return ""

    def _strip_quotes(self, body):
        """引用返信部分を削除する"""
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
        
        return "\n".join(cleaned_lines).strip()

    def _save_inquiry_message(self, inquiry, body):
        """InquiryMessageを保存し、ステータスを更新する"""
        InquiryMessage.objects.create(
            inquiry=inquiry,
            sender_type='user',
            message=body,
            created_at=timezone.now()
        )
        
        if inquiry.status == 'completed':
            inquiry.status = 'in_progress'
            inquiry.save()
