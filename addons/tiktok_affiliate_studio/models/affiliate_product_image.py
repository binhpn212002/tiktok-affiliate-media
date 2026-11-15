import base64
import binascii
import hashlib
import io

from PIL import Image
from PIL import WebPImagePlugin  # noqa: F401  # Register WebP with Pillow after Odoo preloads its image plugins.

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..services.r2_storage import upload_objects
_IMAGE_TYPES = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"), "WEBP": ("webp", "image/webp")}
_MAX_IMAGE_BYTES = 10 * 1024 * 1024


class AffiliateProductImage(models.Model):
    _name = "affiliate.product.image"
    _description = "Affiliate Product Image"
    _rec_name = "url"

    product_id = fields.Many2one("affiliate.product", required=True, ondelete="cascade", index=True)
    url = fields.Char(required=True, readonly=True)
    upload = fields.Binary(compute="_compute_upload", inverse="_inverse_upload", attachment=False)
    filename = fields.Char(compute="_compute_upload", inverse="_inverse_upload")

    def _compute_upload(self):
        for image in self:
            image.upload = False
            image.filename = False

    def _inverse_upload(self):
        if any(image.upload for image in self):
            raise UserError(_("Add a new image row to upload another file."))

    @api.model_create_multi
    def create(self, vals_list):
        self.check_access_rights("create")
        uploads = []
        for index, vals in enumerate(vals_list, start=1):
            label = vals.get("filename") or _("Image %(index)s", index=index)
            upload = vals.get("upload")
            if not upload:
                raise ValidationError(_("%(file)s: choose an image file to upload.", file=label))
            try:
                data = base64.b64decode(upload, validate=True)
            except (ValueError, TypeError, binascii.Error) as error:
                raise ValidationError(_(
                    "%(file)s: the upload data is invalid. Remove this row and select the file again.",
                    file=label,
                )) from error

            if not data or len(data) > _MAX_IMAGE_BYTES:
                raise ValidationError(_("%(file)s: choose an image up to 10 MB.", file=label))
            try:
                with Image.open(io.BytesIO(data)) as image:
                    image_format = image.format
                    image.verify()
            except (ValueError, OSError, SyntaxError, Image.DecompressionBombError) as error:
                raise ValidationError(_(
                    "%(file)s: the image could not be read. Re-export it as JPEG, PNG or WebP.",
                    file=label,
                )) from error
            if image_format not in _IMAGE_TYPES:
                raise ValidationError(_(
                    "%(file)s: detected %(format)s. Re-export it as JPEG, PNG or WebP.",
                    file=label, format=image_format or _("unknown format"),
                ))
            extension, content_type = _IMAGE_TYPES[image_format]
            checksum = hashlib.sha256(data).hexdigest()
            key = f"product-images/{checksum}.{extension}"
            uploads.append((key, data, content_type))

        urls = upload_objects(uploads)
        return super().create([
            {"product_id": vals.get("product_id"), "url": url}
            for vals, url in zip(vals_list, urls)
        ])
