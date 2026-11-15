def migrate(cr, version):
    cr.execute("""
        ALTER TABLE affiliate_product
        DROP COLUMN IF EXISTS sku,
        DROP COLUMN IF EXISTS tiktok_product_id
    """)
