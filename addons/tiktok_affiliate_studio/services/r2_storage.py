import logging
import os
from urllib.parse import urlsplit

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def upload_objects(objects):
    endpoint, bucket, access_key, secret_key, public_url = (
        os.environ.get(name, "").strip()
        for name in ("R2_ENDPOINT_URL", "R2_BUCKET", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_PUBLIC_BASE_URL")
    )
    if not all((endpoint, bucket, access_key, secret_key, public_url)):
        raise UserError(_("Configure R2 on the Odoo server before uploading media."))
    for address in (endpoint, public_url):
        parsed = urlsplit(address)
        if parsed.scheme != "https" or not parsed.hostname or parsed.query or parsed.fragment:
            raise UserError(_("R2 endpoint and public base URL must be HTTPS URLs."))

    try:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as error:
        raise UserError(_("Install boto3 in the Odoo Python environment to use R2.")) from error

    try:
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
            config=Config(connect_timeout=5, read_timeout=30, retries={"total_max_attempts": 2}),
        )
        for key, data, content_type in objects:
            client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
    except (BotoCoreError, ClientError) as error:
        _logger.warning("R2 media upload failed (%s)", type(error).__name__)
        raise UserError(_("Could not upload media to R2. Check the bucket configuration and try again.")) from error
    return [f"{public_url.rstrip('/')}/{key}" for key, _, _ in objects]
