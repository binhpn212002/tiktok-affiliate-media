/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FileUploader } from "@web/views/fields/file_handler";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

class ProductImages extends X2ManyField {
    static template = "tiktok_affiliate_studio.ProductImages";
    static components = { ...X2ManyField.components, FileUploader };

    async addImage({ name, data }) {
        const record = await this.list.addNewRecord({ position: "bottom", mode: "readonly" });
        await record.update({ upload: data, filename: name });
    }
}

registry.category("fields").add("affiliate_product_images", {
    ...x2ManyField,
    component: ProductImages,
});
