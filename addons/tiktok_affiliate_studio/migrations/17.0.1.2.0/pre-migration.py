def migrate(cr, version):
    cr.execute("ALTER TABLE affiliate_product DROP COLUMN IF EXISTS shop_name")
